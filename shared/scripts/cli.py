#!/usr/bin/env python3
"""Cross-platform m-edit command dispatcher.

`bin/m-edit` (bash) and `bin/m-edit.ps1` (PowerShell) both call this file, so a command is added
once here instead of in two shell routing tables.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]

ROUTES = {
    # project state
    'init': ('state.py', True),
    'sync-clips': ('state.py', True),
    'begin-transcription': ('state.py', True),
    'status': ('state.py', True),
    'approve-merge': ('state.py', True),
    'mark-merged': ('state.py', True),
    # the edit: interview -> autonomous edit -> one review -> finals
    'await-direction': ('director.py', True),
    'record-direction': ('director.py', True),
    'record-preview': ('director.py', True),
    'await-reel-approval': ('director.py', True),
    'approve-reel': ('director.py', True),
    'mark-reel-final': ('director.py', True),
    'reopen-reel': ('director.py', True),
    # editing rules as code
    'camera': ('edit_audit.py', True),
    'audit-edit': ('edit_audit.py', 'audit'),
    'edit-props': ('edit_props.py', False),
    # media and integrity tools
    'scan-clips': ('scan_clips.py', False),
    'guard': ('guard.py', False),
    'recipe': ('recipe.py', False),
    'transcribe': ('transcribe.py', False),
    'captions': ('captions.py', False),
    'verify': ('verify_media.py', False),
    'doctor': ('doctor.py', False),
    'scaffold-remotion': ('scaffold_remotion.py', False),
    'validate-config': ('validate_config.py', False),
    'release-audit': ('release_audit.py', False),
}

HELP = """m-edit command line

Start:
  m-edit doctor --project DIR            what is installed, what is missing
  m-edit init --project DIR
  m-edit scan-clips --project DIR
  m-edit sync-clips --project DIR
  m-edit status --project DIR

The edit (called by the m-edit skills):
  await-direction | record-direction | record-preview | await-reel-approval
  approve-reel | mark-reel-final | reopen-reel | approve-merge | mark-merged

Editing rules as code:
  m-edit camera --duration S [--punch T ...] [--jump T ...] [--seed N]
  m-edit audit-edit --edit FILE --output REPORT [--config CONFIG]
  m-edit edit-props --edit FILE --clip ID --preset preview|final --output PROPS

Media and integrity:
  m-edit recipe create|verify ...      m-edit verify ...
  m-edit captions import|validate|chunk|export-srt ...
  m-edit transcribe detect|run ...     m-edit guard --kind preview|final|merge ...
  m-edit scaffold-remotion --project DIR
"""


def run(script: str, argv: list[str]) -> None:
    sys.argv = [str(SCRIPTS / script), *argv]
    sys.path.insert(0, str(SCRIPTS))
    runpy.run_path(str(SCRIPTS / script), run_name='__main__')


def main() -> None:
    args = sys.argv[1:]
    command = args[0] if args else 'help'
    rest = args[1:]
    if command in ROUTES:
        script, subcommand = ROUTES[command]
        if subcommand is True:
            run(script, [command, *rest])
        elif subcommand:
            run(script, [subcommand, *rest])
        else:
            run(script, rest)
    elif command == 'version':
        print((ROOT / 'VERSION').read_text(encoding='utf-8').strip())
    elif command in {'help', '-h', '--help'}:
        print(HELP)
    else:
        print(f'Unknown command: {command}', file=sys.stderr)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
