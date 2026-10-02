#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
MAX_FRONTMATTER_BYTES = 1024
MAX_DESCRIPTION_CHARS = 500


def parse_skill(path: Path) -> tuple[dict, str, str]:
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise ValueError('missing opening YAML delimiter')
    parts = text.split('---', 2)
    if len(parts) != 3:
        raise ValueError('missing closing YAML delimiter')
    raw = parts[1].strip() + '\n'
    metadata = yaml.safe_load(raw)
    if not isinstance(metadata, dict):
        raise ValueError('frontmatter must be a mapping')
    return metadata, parts[2].strip(), raw


def validate(root: Path) -> list[str]:
    findings: list[str] = []
    skills = root / 'skills'
    if not skills.is_dir():
        return ['skills/: missing']
    for directory in sorted(path for path in skills.iterdir() if path.is_dir()):
        path = directory / 'SKILL.md'
        relative = path.relative_to(root).as_posix()
        if not path.exists():
            findings.append(f'{directory.name}: missing SKILL.md')
            continue
        try:
            metadata, body, raw = parse_skill(path)
        except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
            findings.append(f'{relative}: {exc}')
            continue
        name = metadata.get('name')
        description = metadata.get('description')
        if name != directory.name:
            findings.append(f'{relative}: name must equal directory name')
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            findings.append(f'{relative}: invalid skill name')
        if not isinstance(description, str) or not description.strip():
            findings.append(f'{relative}: missing description')
        else:
            description = description.strip()
            if not description.startswith('Use when'):
                findings.append(f'{relative}: description should start with "Use when"')
            if len(description) > MAX_DESCRIPTION_CHARS:
                findings.append(f'{relative}: description exceeds {MAX_DESCRIPTION_CHARS} characters')
            process_shortcuts = (' then ', 'step 1', 'first ', 'workflow:')
            if any(token in description.lower() for token in process_shortcuts):
                findings.append(f'{relative}: description appears to summarize workflow instead of trigger conditions')
        if len(raw.encode('utf-8')) > MAX_FRONTMATTER_BYTES:
            findings.append(f'{relative}: frontmatter exceeds {MAX_FRONTMATTER_BYTES} bytes')
        if not body:
            findings.append(f'{relative}: empty body')
        if 'STOP' not in body and directory.name in {
            'm-edit-transcribe', 'm-edit-final', 'm-edit-merge', 'm-edit-interview', 'm-edit-direct',
        }:
            findings.append(f'{relative}: gated workflow does not contain an explicit STOP marker')
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description='Validate m-edit Agent Skills metadata and gate markers.')
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    findings = validate(root)
    if findings:
        print('\n'.join(findings))
        raise SystemExit(f'Skill validation failed with {len(findings)} finding(s)')
    print('Skill validation passed')


if __name__ == '__main__':
    main()
