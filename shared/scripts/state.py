#!/usr/bin/env python3
"""m-edit project state: initialization, source-clip integrity, transcription reset, status and merge.

The editing transitions (interview, previews, whole-video review, finals) live in director.py.
The project context that approvals bind to is the clip inventory plus config: m-edit reads no
instruction files.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from common import (
    append_jsonl,
    digest_json,
    now,
    project_lock,
    project_relative,
    read_json,
    sha256,
    write_json,
)

SCHEMA_VERSION = 3
PHASES = {
    'uninitialized', 'transcribing', 'awaiting_direction', 'directing', 'awaiting_reel_approval',
    'finalizing_reel', 'all_clips_complete', 'merge_approved', 'complete',
}


def suite_root() -> Path:
    return Path(__file__).resolve().parents[1]


def paths(project: str) -> tuple[Path, Path, Path]:
    root = Path(project).expanduser().resolve()
    control = root / '.m-edit'
    return root, control, control / 'state.json'


def load(project: str) -> tuple[Path, Path, Path, dict[str, Any]]:
    root, control, state_path = paths(project)
    if not state_path.exists():
        raise SystemExit(f'Missing {state_path}; run init')
    data = read_json(state_path)
    if data.get('schema_version') != SCHEMA_VERSION:
        raise SystemExit('This .m-edit folder was created by m-edit 1.x. Finish it with the 1.x release, '
                         'or rename .m-edit and start again with m-edit 2.')
    if data.get('phase') not in PHASES:
        raise SystemExit(f'Invalid phase: {data.get("phase")}')
    return root, control, state_path, data


def save(path: Path, data: dict[str, Any], event: str) -> None:
    data['updated_at'] = now()
    history = data.setdefault('history', [])
    history.append({'at': data['updated_at'], 'phase': data['phase'], 'event': event})
    if len(history) > 2000:
        del history[:-2000]
    write_json(path, data)


def source_paths(data: dict[str, Any]) -> set[str]:
    return set(data.get('clip_order', []))


def safe_output(root: Path, data: dict[str, Any], value: str, *, must_exist: bool = True) -> tuple[Path, str]:
    path, relative = project_relative(root, value, must_exist=must_exist)
    if relative in source_paths(data):
        raise SystemExit('Generated output may not overwrite a source clip')
    return path, relative


def fresh_clip_record(fingerprint: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        'status': 'pending',
        'source_fingerprint': fingerprint,
        'preview_version': 0,
        'preview_path': None,
        'preview_hash': None,
        'preview_verification_path': None,
        'recipe_path': None,
        'recipe_hash': None,
        'recipe_bundle_digest': None,
        'bound_digest': None,
        'approved_preview_hash': None,
        'approved_recipe_hash': None,
        'approved_recipe_bundle_digest': None,
        'approved_guide_hash': None,
        'preview_approval_receipt_id': None,
        'final_path': None,
        'final_hash': None,
        'verification_path': None,
    }


def invalidate_downstream(data: dict[str, Any]) -> None:
    data['guide']['hash'] = None
    data['direction'].update({'hash': None, 'receipt_id': None, 'answered_at': None})
    data['reel_review'].update({'path': None, 'hash': None, 'approved_digest': None, 'receipt_id': None})
    data['merge'] = {'approved': False, 'approval_receipt_id': None, 'path': None, 'hash': None, 'verification_path': None}
    for name, clip in data.get('clips', {}).items():
        data['clips'][name] = fresh_clip_record(clip.get('source_fingerprint'))


# ------------------------------------------------------------------ context: clips + config
def context_paths(root: Path, data: dict[str, Any]) -> dict[str, Path]:
    context = data['context']
    return {
        'config_hash': root / context['config_path'],
        'clip_inventory_hash': root / context['clip_inventory_path'],
    }


def verify_source_inventory(root: Path, inventory: dict[str, Any]) -> None:
    clips = inventory.get('clips')
    if not isinstance(clips, list) or not clips:
        raise SystemExit('No source clips are recorded in the inventory')
    for record in clips:
        path, relative = project_relative(root, str(record.get('path')), must_exist=True)
        fingerprint = record.get('fingerprint') or {}
        stat = path.stat()
        if stat.st_size != fingerprint.get('size_bytes'):
            raise SystemExit(f'Source clip size changed: {relative}')
        if fingerprint.get('hash_mode') == 'full':
            expected = fingerprint.get('sha256')
            if not expected or sha256(path) != expected:
                raise SystemExit(f'Source clip content changed: {relative}')
        elif stat.st_mtime_ns != fingerprint.get('mtime_ns'):   # stat-only hashing: a touch counts as a change
            raise SystemExit(f'Source clip timestamp changed under stat-only hashing: {relative}')


def inventory_digest(inventory: dict[str, Any]) -> str:
    """The clips' identity: under full hashing a timestamp-only change (a touch, a copy) is not a change."""
    records = []
    for record in inventory.get('clips', []):
        record = json.loads(json.dumps(record))
        fingerprint = record.get('fingerprint') or {}
        if fingerprint.get('hash_mode') == 'full':
            fingerprint.pop('mtime_ns', None)
        for volatile in ('scanned_at', 'probe'):
            record.pop(volatile, None)
        records.append(record)
    return digest_json(records)


# Operational settings: granting a download, setting up a matte model or raising a render timeout after the
# answers must not reset the edit. Everything else in the config shapes the edit and is bound.
OPERATIONAL = {'assets': None, 'depth': None, 'render': ('renderer_timeout_ms', 'retry_concurrency'),
               'transcription': ('allow_network',)}


def config_digest(config: dict[str, Any]) -> str:
    bound = json.loads(json.dumps(config))
    for section, keys in OPERATIONAL.items():
        if keys is None:
            bound.pop(section, None)
        elif isinstance(bound.get(section), dict):
            for key in keys:
                bound[section].pop(key, None)
    return digest_json(bound)


def context_hashes(root: Path, data: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for field, path in context_paths(root, data).items():
        if not path.exists():
            raise SystemExit(f'Missing context artifact: {path}')
        values[field] = inventory_digest(read_json(path)) if field == 'clip_inventory_hash' else config_digest(read_json(path))
    return values


def current_context_digest(root: Path, data: dict[str, Any], *, verify_sources: bool = True) -> str:
    values = context_hashes(root, data)
    if verify_sources:
        verify_source_inventory(root, read_json(context_paths(root, data)['clip_inventory_hash']))
    return digest_json(values)


def record_context(root: Path, data: dict[str, Any]) -> None:
    data['context'].update(context_hashes(root, data))
    data['context']['context_digest'] = current_context_digest(root, data)


def guard_context(root: Path, data: dict[str, Any]) -> None:
    current = context_hashes(root, data)
    for field, value in current.items():
        if data['context'].get(field) != value:
            raise SystemExit(f'Project context changed: {field}')
    actual = current_context_digest(root, data)
    if not data['context'].get('context_digest') or actual != data['context']['context_digest']:
        raise SystemExit('Project context changed: source clip content mismatch')


def record_approval(control: Path, kind: str, artifact_hash: str, evidence: str) -> str:
    evidence = (evidence or '').strip()
    if len(evidence) < 2:
        raise SystemExit('Record the user\'s exact message as evidence')
    receipt = {'at': now(), 'kind': kind, 'artifact_hash': artifact_hash, 'evidence': evidence}
    receipt['id'] = digest_json(receipt)[:20]
    append_jsonl(control / 'approvals.jsonl', receipt)
    return receipt['id']


def validate_verification(media_path: Path, verification_path: Path, *, preview_hash: str | None = None,
                          min_ssim: float | None = None) -> dict[str, Any]:
    verification = read_json(verification_path)
    if verification.get('passed') is not True:
        raise SystemExit('Verification JSON does not report passed: true')
    if verification.get('sha256') != sha256(media_path):
        raise SystemExit('Verification JSON hash does not match media')
    if preview_hash is not None:
        comparison = verification.get('comparison')
        if not isinstance(comparison, dict):
            raise SystemExit('Final verification is missing the preview-fidelity comparison')
        if comparison.get('preview_sha256') != preview_hash:
            raise SystemExit('Final verification compared against the wrong preview')
        if min_ssim is not None:
            score = comparison.get('ssim')
            if not isinstance(score, (int, float)) or score < min_ssim:
                raise SystemExit(f'Final visual fidelity is below the configured SSIM threshold: {score}')
    return verification


# ------------------------------------------------------------------ commands
def init(project: str) -> None:
    root, control, state_path = paths(project)
    if not root.is_dir():
        raise SystemExit(f'Missing project folder: {root}')
    control.mkdir(parents=True, exist_ok=True)
    with project_lock(control):
        config_path = control / 'config.json'
        if not config_path.exists():
            shutil.copyfile(suite_root() / 'templates' / 'config.template.json', config_path)
        if not state_path.exists():
            data = read_json(suite_root() / 'templates' / 'state.template.json')
            data['project_root'] = str(root)
            data['created_at'] = now()
            data['updated_at'] = data['created_at']
            data['history'] = [{'at': data['created_at'], 'phase': 'uninitialized', 'event': 'initialized'}]
            write_json(state_path, data)
    print(state_path)


def sync_clips(project: str) -> None:
    root, control, state_path, data = load(project)
    inventory_path = control / 'clip_inventory.json'
    if not inventory_path.exists():
        raise SystemExit('Missing clip inventory; run scan-clips')
    inventory = read_json(inventory_path)
    order = [clip['path'] for clip in inventory.get('clips', [])]
    if not order:
        raise SystemExit('No source clips found')
    fingerprints = {clip['path']: clip.get('fingerprint') for clip in inventory.get('clips', [])}
    with project_lock(control):
        was_directed = bool(data['direction'].get('hash'))
        changed = False
        if was_directed:
            try:
                guard_context(root, data)
            except SystemExit:
                changed = True
        old_order = list(data.get('clip_order', []))
        data['clip_order'] = order
        for clip in order:
            record = data.setdefault('clips', {}).get(clip)
            if not isinstance(record, dict):
                data['clips'][clip] = fresh_clip_record(fingerprints.get(clip))
            data['clips'][clip]['source_fingerprint'] = fingerprints.get(clip)
        for stale in list(data.get('clips', {})):
            if stale not in order:
                del data['clips'][stale]
        if old_order and old_order != order:
            changed = changed or was_directed
        if changed:
            data['phase'] = 'transcribing'
            invalidate_downstream(data)
            event = 'source clips changed; direction, previews and approvals invalidated'
        else:
            event = 'clip inventory synchronized'
        save(state_path, data, event)
    print(json.dumps({'clip_order': order, 'invalidated': changed}, indent=2))


def begin_transcription(project: str, reason: str) -> None:
    root, control, state_path, data = load(project)
    with project_lock(control):
        data['phase'] = 'transcribing'
        invalidate_downstream(data)
        record_context(root, data)
        save(state_path, data, reason)
    print('transcribing')


def approve_merge(project: str, evidence: str) -> None:
    _, control, state_path, data = load(project)
    if data['phase'] != 'all_clips_complete':
        raise SystemExit('Every final must be complete before a merge')
    finals = digest_json([data['clips'][clip].get('final_hash') for clip in data['clip_order']])
    with project_lock(control):
        receipt = record_approval(control, 'merge', finals, evidence)
        data['merge']['approved'] = True
        data['merge']['approval_receipt_id'] = receipt
        data['phase'] = 'merge_approved'
        save(state_path, data, 'merge explicitly requested')
    print('merge_approved')


def mark_merged(project: str, path: str, verification: str) -> None:
    root, control, state_path, data = load(project)
    guard_context(root, data)
    if data['phase'] != 'merge_approved' or not data['merge'].get('approved'):
        raise SystemExit('Merge was not explicitly requested')
    for clip in data['clip_order']:
        record = data['clips'][clip]
        final, _ = safe_output(root, data, record['final_path'])
        if sha256(final) != record.get('final_hash'):
            raise SystemExit(f'Final changed before merge: {clip}')
    merged, merged_relative = safe_output(root, data, path)
    verification_path, verification_relative = safe_output(root, data, verification)
    validate_verification(merged, verification_path)
    with project_lock(control):
        data['merge'].update({'path': merged_relative, 'hash': sha256(merged), 'verification_path': verification_relative})
        data['phase'] = 'complete'
        save(state_path, data, 'merged output recorded')
    print(data['merge']['hash'])


def status(project: str) -> None:
    root, _, _, data = load(project)
    warnings: list[str] = []
    if data['direction'].get('hash'):
        try:
            guard_context(root, data)
        except SystemExit as exc:
            warnings.append(str(exc))
    output = dict(data)
    output['warnings'] = warnings
    print(json.dumps(output, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description='m-edit project state')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'sync-clips', 'status'):
        sub.add_parser(name).add_argument('--project', required=True)
    c = sub.add_parser('begin-transcription')
    c.add_argument('--project', required=True)
    c.add_argument('--reason', default='transcription started')
    c = sub.add_parser('approve-merge')
    c.add_argument('--project', required=True)
    c.add_argument('--evidence', required=True)
    c = sub.add_parser('mark-merged')
    for flag in ('--project', '--path', '--verification'):
        c.add_argument(flag, required=True)
    a = parser.parse_args()
    {
        'init': lambda: init(a.project),
        'sync-clips': lambda: sync_clips(a.project),
        'status': lambda: status(a.project),
        'begin-transcription': lambda: begin_transcription(a.project, a.reason),
        'approve-merge': lambda: approve_merge(a.project, a.evidence),
        'mark-merged': lambda: mark_merged(a.project, a.path, a.verification),
    }[a.command]()


if __name__ == '__main__':
    main()
