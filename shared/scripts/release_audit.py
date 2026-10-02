#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TEXT_EXTENSIONS = {'.md', '.txt', '.json', '.py', '.sh', '.ps1', '.yaml', '.yml', '.ts', '.tsx', ''}
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'dist', 'build', '.venv', 'venv'}
BINARY_EXTENSIONS = {
    '.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.mp3', '.wav', '.aac', '.flac',
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.pyc', '.zip', '.tar', '.gz', '.7z', '.exe', '.dll',
}
SECRET_PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'generic secret assignment': re.compile(r'(?i)(api[_-]?key|client[_-]?secret|access[_-]?token|password)\s*[:=]\s*["\'][^"\']{12,}["\']'),
    'GitHub token': re.compile(r'\bgh[opusr]_[A-Za-z0-9_]{30,}\b'),
    'OpenAI token': re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    'AWS access key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    'email address': re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I),
    'absolute Unix home path': re.compile(r'/(?:Users|home)/[^/\s]+/'),
    'absolute Windows user path': re.compile(r'(?i)\b[A-Z]:\\Users\\[^\\\s]+\\'),
    'build-container path': re.compile(r'/(?:mnt/data|tmp)/(?:[^\s`"\']+/){1,}'),
}
UNSAFE_CODE_PATTERNS = {
    'Python shell=True': re.compile(r'subprocess\.(?:run|Popen|call)\([^\n]*shell\s*=\s*True'),
    'Python os.system': re.compile(r'\bos\.system\s*\('),
}


def load_private_denylist(path: str | None) -> list[tuple[str, re.Pattern[str]]]:
    if not path:
        return []
    source = Path(path).expanduser().resolve(strict=True)
    patterns = []
    for index, line in enumerate(source.read_text(encoding='utf-8').splitlines(), 1):
        phrase = line.strip()
        if not phrase or phrase.startswith('#'):
            continue
        patterns.append((f'private denylist phrase #{index}', re.compile(re.escape(phrase), re.I)))
    return patterns


def main() -> None:
    parser = argparse.ArgumentParser(description='Audit an m-edit source tree for secrets, private denylist phrases, and release hazards.')
    parser.add_argument('--root', required=True)
    parser.add_argument('--private-denylist', help='Optional uncommitted file with one private literal phrase per line.')
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    findings: list[str] = []
    if not root.is_dir():
        raise SystemExit(f'Missing release root: {root}')
    private_patterns = load_private_denylist(args.private_denylist)

    for path in sorted(root.rglob('*')):
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            findings.append(f'{relative}: symlinks are not allowed in the source release archive')
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in BINARY_EXTENSIONS:
            findings.append(f'{relative}: binary/generated artifact is not allowed in the source package')
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in {'LICENSE', 'VERSION'}:
            findings.append(f'{relative}: unreviewed file type')
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            findings.append(f'{relative}: unreadable non-text file')
            continue
        if path.resolve() != Path(__file__).resolve():
            for label, pattern in [*SECRET_PATTERNS.items(), *private_patterns]:
                if pattern.search(text):
                    findings.append(f'{relative}: possible {label}')
        if path.suffix == '.py':
            for label, pattern in UNSAFE_CODE_PATTERNS.items():
                if pattern.search(text):
                    findings.append(f'{relative}: {label}')

    version = (root / 'VERSION').read_text(encoding='utf-8').strip() if (root / 'VERSION').exists() else None
    if not version:
        findings.append('VERSION: missing or empty')
    for manifest_name in ('.claude-plugin/plugin.json', '.claude-plugin/marketplace.json'):
        manifest_path = root / manifest_name
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            findings.append(f'{manifest_name}: invalid or missing ({exc})')
            continue
        manifest_versions: list[str] = []
        if manifest.get('version'):
            manifest_versions.append(str(manifest['version']))
        for plugin in manifest.get('plugins', []) if isinstance(manifest.get('plugins'), list) else []:
            if plugin.get('version'):
                manifest_versions.append(str(plugin['version']))
        for value in manifest_versions:
            if version and value != version:
                findings.append(f'{manifest_name}: version {value} does not match VERSION {version}')

    for skill_file in sorted((root / 'skills').glob('*/SKILL.md')):
        text = skill_file.read_text(encoding='utf-8')
        match = re.search(r'(?m)^\s*version:\s*["\']?([^"\'\s]+)', text)
        if not match or (version and match.group(1) != version):
            findings.append(f'{skill_file.relative_to(root)}: metadata version does not match VERSION')

    if findings:
        print('\n'.join(findings))
        raise SystemExit(f'Release audit failed with {len(findings)} finding(s)')
    print('Release audit passed')


if __name__ == '__main__':
    main()
