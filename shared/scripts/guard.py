#!/usr/bin/env python3
"""Block an unsafe transition before work starts: previews while directing, finals after the whole-video
approval, merge only on an explicit request."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import read_json, sha256
from state import guard_context, safe_output


def director_guard(root: Path, state: dict, kind: str, clip: str | None) -> None:
    from director import bound_digest, check_clip_preview, guard_direction
    guard_direction(root, state)
    if kind == 'preview':
        if state['phase'] not in {'directing', 'awaiting_reel_approval'}:
            raise SystemExit(f'BLOCKED: preview is not allowed from {state["phase"]}')
    elif kind == 'final':
        if state['phase'] != 'finalizing_reel':
            raise SystemExit(f'BLOCKED: final is not allowed from {state["phase"]}')
        targets = [clip] if clip else list(state['clip_order'])
        bound = bound_digest(root, state)
        for name in targets:
            record = state['clips'].get(name) or {}
            if not record.get('approved_preview_hash'):
                raise SystemExit(f'BLOCKED: {name} has no approved preview')
            check_clip_preview(root, state, name, bound)
    else:
        if state['phase'] != 'merge_approved' or not state['merge'].get('approved'):
            raise SystemExit('BLOCKED: merge was not explicitly approved')
        for name in state['clip_order']:
            record = state['clips'][name]
            if record.get('status') != 'complete':
                raise SystemExit(f'BLOCKED: incomplete final for {name}')
            final, _ = safe_output(root, state, record['final_path'])
            if sha256(final) != record.get('final_hash'):
                raise SystemExit(f'BLOCKED: final changed for {name}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Block unsafe m-edit transitions before work starts.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--kind', choices=['preview', 'final', 'merge'], required=True)
    parser.add_argument('--clip')
    args = parser.parse_args()
    root = Path(args.project).expanduser().resolve()
    state = read_json(root / '.m-edit' / 'state.json')
    guard_context(root, state)
    director_guard(root, state, args.kind, args.clip)
    print(f'ALLOWED: {args.kind}')


if __name__ == '__main__':
    main()
