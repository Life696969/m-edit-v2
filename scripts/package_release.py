#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import stat
import zipfile
from pathlib import Path

EXCLUDED_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'dist', 'build', '.m-edit', '.m-edit-suite', 'node_modules'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo', '.zip', '.sha256'}
FIXED_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def files(root: Path):
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if not path.is_file() or path.is_symlink() or path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        yield path, relative


def main() -> None:
    parser = argparse.ArgumentParser(description='Build a deterministic m-edit source ZIP and SHA-256 file.')
    parser.add_argument('--root', default='.')
    parser.add_argument('--dist', default='dist')
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    version = (root / 'VERSION').read_text(encoding='utf-8').strip()
    dist = Path(args.dist)
    if not dist.is_absolute():
        dist = root / dist
    dist.mkdir(parents=True, exist_ok=True)
    archive = dist / f'm-edit-{version}.zip'
    top = f'm-edit-{version}'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path, relative in files(root):
            info = zipfile.ZipInfo(f'{top}/{relative.as_posix()}', FIXED_TIMESTAMP)
            mode = path.stat().st_mode
            executable = bool(mode & stat.S_IXUSR) or path.name in {'install.sh', 'uninstall.sh', 'm-edit'} or path.suffix == '.py'
            info.external_attr = ((0o755 if executable else 0o644) & 0xFFFF) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, path.read_bytes())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(archive.suffix + '.sha256')
    checksum.write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(archive)
    print(checksum)


if __name__ == '__main__':
    main()
