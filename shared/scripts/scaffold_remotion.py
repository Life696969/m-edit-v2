#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import project_relative


def main() -> None:
    parser = argparse.ArgumentParser(description='Copy the bundled generic Remotion starter into a project without installing packages.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--target', default='m-edit-remotion')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve(strict=True)
    target, relative = project_relative(project, args.target, must_exist=False)
    source = Path(__file__).resolve().parents[1] / 'remotion-starter'
    if target.exists() and not args.force:
        raise SystemExit(f'Target already exists: {relative}. Refusing to overwrite without --force.')
    if target.exists():
        shutil.rmtree(target)
    temporary = target.with_name(f'.{target.name}.tmp')
    shutil.rmtree(temporary, ignore_errors=True)
    shutil.copytree(source, temporary)
    temporary.replace(target)
    print(f'Scaffolded generic Remotion project at {relative}. Dependencies were not installed.')


if __name__ == '__main__':
    main()
