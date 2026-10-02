#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description='Run black-box m-edit behavior evaluations against a configured coding-agent command.')
    parser.add_argument('--cases', default=str(Path(__file__).with_name('cases.json')))
    parser.add_argument('--command', default=os.environ.get('M_EDIT_EVAL_COMMAND'))
    parser.add_argument('--output', default='evals/results.json')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    if not args.command:
        raise SystemExit('Set --command or M_EDIT_EVAL_COMMAND. Use {prompt} as the prompt placeholder.')
    payload = json.loads(Path(args.cases).read_text(encoding='utf-8'))
    results = []
    for case in payload['cases']:
        command = args.command.split()
        expanded = [case['prompt'] if token == '{prompt}' else token for token in command]
        if '{prompt}' not in command:
            raise SystemExit('The command template must contain {prompt} as a standalone argument')
        completed = subprocess.run(expanded, text=True, capture_output=True, timeout=args.timeout)
        text = (completed.stdout + '\n' + completed.stderr).strip()
        lower = text.lower()
        missing = [token for token in case.get('must_include', []) if token.lower() not in lower]
        forbidden = [token for token in case.get('must_not_include', []) if token.lower() in lower]
        results.append({
            'id': case['id'],
            'returncode': completed.returncode,
            'passed': completed.returncode == 0 and not missing and not forbidden,
            'missing': missing,
            'forbidden': forbidden,
            'output': text,
        })
    report = {
        'schema_version': 1,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'command_template': args.command,
        'results': results,
        'passed': all(item['passed'] for item in results),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'results'}, indent=2))
    if not report['passed']:
        raise SystemExit('One or more agent behavior evaluations failed')


if __name__ == '__main__':
    main()
