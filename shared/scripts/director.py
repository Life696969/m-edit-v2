#!/usr/bin/env python3
"""m-edit editing workflow: one direction interview, an autonomous edit, one whole-video review,
individual verified finals.

    transcribing -> awaiting_direction [STOP] -> directing -> awaiting_reel_approval [STOP]
      -> finalizing_reel -> all_clips_complete [STOP] -> (explicit merge only)

A clip preview is bound to a digest of the transcript, the answered direction, the editing guide, the
edit data and its passing audit. Changing any of them after a preview is recorded invalidates that
preview's eligibility for approval; changing them after approval blocks the final.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import digest_json, now, project_lock, project_relative, read_json, sha256
from recipe import verify as verify_recipe
from state import (
    fresh_clip_record,
    guard_context,
    load,
    record_approval,
    record_context,
    safe_output,
    save,
    validate_verification,
)

ANSWERS_HEADING = '## Answers'


def director_fields(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    direction = data.setdefault('direction', {'path': 'direction.md', 'hash': None, 'receipt_id': None, 'answered_at': None})
    edit = data.setdefault('edit', {'path': '.m-edit/edit.json', 'audit_path': '.m-edit/edit_audit.json'})
    review = data.setdefault('reel_review', {'path': None, 'hash': None, 'approved_digest': None, 'receipt_id': None})
    return direction, edit, review


def reset_reel(data: dict[str, Any]) -> None:
    """Clear every preview, approval and final (the clip list itself is kept)."""
    _, _, review = director_fields(data)
    review.update({'path': None, 'hash': None, 'approved_digest': None, 'receipt_id': None})
    for name, clip in data.get('clips', {}).items():
        data['clips'][name] = fresh_clip_record(clip.get('source_fingerprint'))


def clear_approvals(data: dict[str, Any]) -> None:
    _, _, review = director_fields(data)
    review.update({'approved_digest': None, 'receipt_id': None})
    for clip in data.get('clips', {}).values():
        clip.update({'approved_preview_hash': None, 'approved_recipe_hash': None, 'approved_recipe_bundle_digest': None,
                     'approved_guide_hash': None, 'preview_approval_receipt_id': None,
                     'final_path': None, 'final_hash': None, 'verification_path': None})
        if clip.get('preview_hash'):
            clip['status'] = 'preview_ready'


def guard_direction(root: Path, data: dict[str, Any]) -> None:
    direction, _, _ = director_fields(data)
    path, _ = project_relative(root, direction['path'], must_exist=True)
    if not direction.get('hash') or sha256(path) != direction['hash']:
        raise SystemExit('The answered direction (direction.md) changed or was never recorded; '
                         'record revisions in the editing guide, or re-run the interview')


def audited_edit(root: Path, data: dict[str, Any]) -> dict[str, str]:
    """The edit data and its passing audit, as hashes. Raises unless the audit passed on the current edit file."""
    _, edit, _ = director_fields(data)
    edit_path, _ = project_relative(root, edit['path'], must_exist=True)
    audit_path, _ = project_relative(root, edit['audit_path'], must_exist=True)
    report = read_json(audit_path)
    if report.get('passed') is not True:
        raise SystemExit(f'The edit audit did not pass ({edit["audit_path"]}); fix the findings and re-run m-edit audit-edit')
    edit_hash = sha256(edit_path)
    if report.get('edit_sha256') != edit_hash:
        raise SystemExit('edit.json changed after its audit; re-run m-edit audit-edit')
    return {'edit': edit_hash, 'audit': sha256(audit_path)}


def bound_digest(root: Path, data: dict[str, Any]) -> str:
    direction, _, _ = director_fields(data)
    transcript, _ = project_relative(root, data['transcript']['path'], must_exist=True)
    guide, _ = project_relative(root, data['guide']['path'], must_exist=True)
    values = {
        'transcript': sha256(transcript),
        'direction': direction.get('hash'),
        'guide': sha256(guide),
        **audited_edit(root, data),
    }
    return digest_json(values)


def await_direction(project: str) -> None:
    root, control, state_path, data = load(project)
    if data['phase'] not in {'transcribing', 'awaiting_direction'}:
        raise SystemExit('The direction interview happens after transcription and before editing')
    transcript, _ = project_relative(root, data['transcript']['path'], must_exist=True)
    direction, _, _ = director_fields(data)
    project_relative(root, direction['path'], must_exist=True)
    with project_lock(control):
        record_context(root, data)
        data['transcript']['hash'] = sha256(transcript)
        direction.update({'hash': None, 'receipt_id': None, 'answered_at': None})
        data['guide']['hash'] = None
        reset_reel(data)
        data['phase'] = 'awaiting_direction'
        save(state_path, data, 'direction interview asked; waiting for the answers')
    print('awaiting_direction')


def record_direction(project: str, evidence: str) -> None:
    root, control, state_path, data = load(project)
    if data['phase'] != 'awaiting_direction':
        raise SystemExit('Not awaiting the direction interview')
    guard_context(root, data)
    direction, _, _ = director_fields(data)
    path, _ = project_relative(root, direction['path'], must_exist=True)
    text = path.read_text(encoding='utf-8')
    if ANSWERS_HEADING not in text or not text.split(ANSWERS_HEADING, 1)[1].strip():
        raise SystemExit(f'Write the user\'s answers under "{ANSWERS_HEADING}" in {direction["path"]} before recording them')
    transcript, _ = project_relative(root, data['transcript']['path'], must_exist=True)
    with project_lock(control):
        current = sha256(path)
        receipt = record_approval(control, 'direction', current, evidence)
        direction.update({'hash': current, 'receipt_id': receipt, 'answered_at': now()})
        data['transcript']['hash'] = sha256(transcript)
        data['phase'] = 'directing'
        save(state_path, data, 'direction answered; directing the edit autonomously')
    print(current)


def record_preview(project: str, clip: str, path: str, recipe: str, verification: str) -> None:
    root, control, state_path, data = load(project)
    if data['phase'] not in {'directing', 'awaiting_reel_approval'}:
        raise SystemExit('Previews are recorded while directing (or as a revision while awaiting review)')
    guard_context(root, data)
    guard_direction(root, data)
    if clip not in data.get('clip_order', []):
        raise SystemExit(f'Unknown clip: {clip!r}')
    preview, relative = safe_output(root, data, path)
    recipe_path, recipe_relative = safe_output(root, data, recipe)
    verification_path, verification_relative = safe_output(root, data, verification)
    payload = verify_recipe(root, recipe_path)
    if payload.get('clip') != clip:
        raise SystemExit('Render recipe belongs to a different clip')
    validate_verification(preview, verification_path)
    bound = bound_digest(root, data)
    with project_lock(control):
        revision = data['phase'] == 'awaiting_reel_approval'
        if revision:
            clear_approvals(data)
            _, _, review = director_fields(data)
            review.update({'path': None, 'hash': None})
        record = data['clips'][clip]
        record['preview_version'] = int(record.get('preview_version', 0)) + 1
        record.update({
            'preview_path': relative,
            'preview_hash': sha256(preview),
            'preview_verification_path': verification_relative,
            'recipe_path': recipe_relative,
            'recipe_hash': sha256(recipe_path),
            'recipe_bundle_digest': payload['bundle_digest'],
            'bound_digest': bound,
            'approved_preview_hash': None,
            'approved_recipe_hash': None,
            'approved_recipe_bundle_digest': None,
            'approved_guide_hash': None,
            'preview_approval_receipt_id': None,
            'status': 'preview_ready',
        })
        data['phase'] = 'directing'
        save(state_path, data, f'preview v{record["preview_version"]} recorded for {clip}' + (' (revision)' if revision else ''))
    print(record['preview_hash'])


def check_clip_preview(root: Path, data: dict[str, Any], name: str, bound: str) -> dict[str, Any]:
    record = data['clips'][name]
    if not record.get('preview_path'):
        raise SystemExit(f'No preview recorded for {name}')
    preview, _ = safe_output(root, data, record['preview_path'])
    recipe_path, _ = safe_output(root, data, record['recipe_path'])
    payload = verify_recipe(root, recipe_path)
    if sha256(preview) != record.get('preview_hash'):
        raise SystemExit(f'Preview changed after it was recorded: {name}')
    if sha256(recipe_path) != record.get('recipe_hash') or payload.get('bundle_digest') != record.get('recipe_bundle_digest'):
        raise SystemExit(f'Render recipe or Remotion inputs changed after the preview was recorded: {name}')
    if record.get('bound_digest') != bound:
        raise SystemExit(f'Transcript, direction, guide or edit data changed after {name}\'s preview was rendered; re-render it')
    return payload


def await_reel_approval(project: str, review_path: str) -> None:
    root, control, state_path, data = load(project)
    if data['phase'] != 'directing':
        raise SystemExit('The whole-video review is requested while directing')
    guard_context(root, data)
    guard_direction(root, data)
    bound = bound_digest(root, data)
    for name in data['clip_order']:
        check_clip_preview(root, data, name, bound)
    review_file, review_relative = safe_output(root, data, review_path)
    with project_lock(control):
        _, _, review = director_fields(data)
        review.update({'path': review_relative, 'hash': sha256(review_file), 'approved_digest': None, 'receipt_id': None})
        data['guide']['hash'] = sha256(project_relative(root, data['guide']['path'], must_exist=True)[0])
        data['phase'] = 'awaiting_reel_approval'
        save(state_path, data, 'every clip previewed; whole-video review requested')
    print(review['hash'])


def reel_digest(data: dict[str, Any]) -> str:
    _, _, review = director_fields(data)
    return digest_json({'review': review.get('hash'),
                        'clips': [[n, data['clips'][n].get('preview_hash'), data['clips'][n].get('recipe_hash')] for n in data['clip_order']]})


def approve_reel(project: str, evidence: str) -> None:
    root, control, state_path, data = load(project)
    if data['phase'] != 'awaiting_reel_approval':
        raise SystemExit('Not awaiting the whole-video review')
    guard_context(root, data)
    guard_direction(root, data)
    _, _, review = director_fields(data)
    review_file, _ = safe_output(root, data, review['path'])
    bound = bound_digest(root, data)
    payloads = {}
    try:
        if sha256(review_file) != review.get('hash'):
            raise SystemExit('The review file changed after it was presented')
        for name in data['clip_order']:
            payloads[name] = check_clip_preview(root, data, name, bound)
    except SystemExit:
        with project_lock(control):
            clear_approvals(data)
            data['phase'] = 'directing'
            save(state_path, data, 'reviewed artifacts changed before approval; back to directing')
        raise
    with project_lock(control):
        digest = reel_digest(data)
        receipt = record_approval(control, 'reel', digest, evidence)
        guide_hash = sha256(project_relative(root, data['guide']['path'], must_exist=True)[0])
        for name in data['clip_order']:
            record = data['clips'][name]
            record.update({
                'approved_preview_hash': record['preview_hash'],
                'approved_recipe_hash': record['recipe_hash'],
                'approved_recipe_bundle_digest': payloads[name]['bundle_digest'],
                'approved_guide_hash': guide_hash,
                'preview_approval_receipt_id': receipt,
                'status': 'preview_approved',
            })
        review.update({'approved_digest': digest, 'receipt_id': receipt})
        data['guide']['hash'] = guide_hash
        data['phase'] = 'finalizing_reel'
        save(state_path, data, 'whole video explicitly approved; every clip authorized for its own final')
    print(digest)


def mark_reel_final(project: str, clip: str, path: str, verification: str) -> None:
    root, control, state_path, data = load(project)
    if data['phase'] != 'finalizing_reel':
        raise SystemExit('Finals are rendered only after the whole-video review is approved')
    guard_context(root, data)
    guard_direction(root, data)
    if clip not in data.get('clip_order', []):
        raise SystemExit(f'Unknown clip: {clip!r}')
    record = data['clips'][clip]
    if record.get('status') not in {'preview_approved', 'complete'} or not record.get('approved_preview_hash'):
        raise SystemExit(f'{clip} has no approved preview')
    bound = bound_digest(root, data)
    check_clip_preview(root, data, clip, bound)
    if record['preview_hash'] != record['approved_preview_hash'] or record['recipe_hash'] != record['approved_recipe_hash']:
        raise SystemExit('Approved preview or recipe mismatch')
    final_path, final_relative = safe_output(root, data, path)
    verification_path, verification_relative = safe_output(root, data, verification)
    config = read_json(root / data['context']['config_path'])
    compare = bool(config.get('verification', {}).get('compare_final_to_preview', True))
    threshold = float(config.get('render', {}).get('fidelity_min_ssim', 0.95))
    validate_verification(final_path, verification_path,
                          preview_hash=record['approved_preview_hash'] if compare else None,
                          min_ssim=threshold if compare else None)
    with project_lock(control):
        record.update({'final_path': final_relative, 'final_hash': sha256(final_path),
                       'verification_path': verification_relative, 'status': 'complete'})
        remaining = [n for n in data['clip_order'] if data['clips'][n]['status'] != 'complete']
        if not remaining:
            data['phase'] = 'all_clips_complete'
            data['current_clip'] = None
        save(state_path, data, f'final verified and recorded for {clip}' + ('' if remaining else '; every final complete'))
    print(json.dumps({'final_hash': record['final_hash'], 'remaining': remaining}))


def reopen_reel(project: str, reason: str) -> None:
    root, control, state_path, data = load(project)
    if data['phase'] not in {'awaiting_reel_approval', 'finalizing_reel', 'all_clips_complete'}:
        raise SystemExit('Nothing to reopen in the current phase')
    if len((reason or '').strip()) < 2:
        raise SystemExit('Record the user\'s change request as --reason')
    with project_lock(control):
        clear_approvals(data)
        _, _, review = director_fields(data)
        review.update({'path': None, 'hash': None})
        data['phase'] = 'directing'
        save(state_path, data, f'reopened for revision: {reason.strip()[:200]}')
    print('directing')


def main() -> None:
    parser = argparse.ArgumentParser(description='m-edit editing workflow')
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('await-direction'); c.add_argument('--project', required=True)
    c = sub.add_parser('record-direction'); c.add_argument('--project', required=True); c.add_argument('--evidence', required=True)
    c = sub.add_parser('record-preview')
    for flag in ('--project', '--clip', '--path', '--recipe', '--verification'):
        c.add_argument(flag, required=True)
    c = sub.add_parser('await-reel-approval'); c.add_argument('--project', required=True); c.add_argument('--review', required=True)
    c = sub.add_parser('approve-reel'); c.add_argument('--project', required=True); c.add_argument('--evidence', required=True)
    c = sub.add_parser('mark-reel-final')
    for flag in ('--project', '--clip', '--path', '--verification'):
        c.add_argument(flag, required=True)
    c = sub.add_parser('reopen-reel'); c.add_argument('--project', required=True); c.add_argument('--reason', required=True)
    a = parser.parse_args()
    {
        'await-direction': lambda: await_direction(a.project),
        'record-direction': lambda: record_direction(a.project, a.evidence),
        'record-preview': lambda: record_preview(a.project, a.clip, a.path, a.recipe, a.verification),
        'await-reel-approval': lambda: await_reel_approval(a.project, a.review),
        'approve-reel': lambda: approve_reel(a.project, a.evidence),
        'mark-reel-final': lambda: mark_reel_final(a.project, a.clip, a.path, a.verification),
        'reopen-reel': lambda: reopen_reel(a.project, a.reason),
    }[a.command]()


if __name__ == '__main__':
    main()
