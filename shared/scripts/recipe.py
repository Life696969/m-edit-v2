#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import digest_json, natural_key, project_relative, read_json, sha256, write_json


def collect_files(root: Path, includes: list[str]) -> list[dict[str, Any]]:
    collected: dict[str, dict[str, Any]] = {}
    for value in includes:
        candidate, relative = project_relative(root, value, must_exist=True)
        paths: list[Path]
        if candidate.is_dir():
            paths = [path for path in candidate.rglob('*') if path.is_file()]
        else:
            paths = [candidate]
        for path in paths:
            resolved = path.resolve(strict=True)
            try:
                rel = resolved.relative_to(root).as_posix()
            except ValueError as exc:
                raise SystemExit(f'Render recipe path escapes project: {path}') from exc
            if any(part in {'.git', '.m-edit', 'node_modules', 'm-edit-output'} for part in Path(rel).parts):
                continue
            stat = resolved.stat()
            collected[rel] = {
                'path': rel,
                'sha256': sha256(resolved),
                'size_bytes': stat.st_size,
            }
    return [collected[key] for key in sorted(collected, key=natural_key)]


def bundle_digest(payload: dict[str, Any]) -> str:
    stable = {
        'schema_version': payload.get('schema_version'),
        'clip': payload.get('clip'),
        'composition_id': payload.get('composition_id'),
        'entry_point': payload.get('entry_point'),
        'input_props': payload.get('input_props'),
        'render_command': payload.get('render_command'),
        'files': payload.get('files'),
    }
    return digest_json(stable)


def verify(root: Path, recipe_path: Path) -> dict[str, Any]:
    payload = read_json(recipe_path)
    if payload.get('schema_version') != 1:
        raise SystemExit('Unsupported render recipe schema')
    files = payload.get('files')
    if not isinstance(files, list) or not files:
        raise SystemExit('Render recipe must contain at least one hashed file')
    for record in files:
        path, relative = project_relative(root, str(record.get('path')), must_exist=True)
        if relative != record.get('path'):
            raise SystemExit(f'Non-canonical render recipe path: {record.get("path")}')
        if sha256(path) != record.get('sha256'):
            raise SystemExit(f'Render recipe input changed: {relative}')
    actual = bundle_digest(payload)
    if actual != payload.get('bundle_digest'):
        raise SystemExit('Render recipe bundle digest mismatch')
    return payload


def create(args: argparse.Namespace) -> None:
    root = Path(args.project).expanduser().resolve(strict=True)
    source, clip = project_relative(root, args.clip, must_exist=True)
    includes = list(args.include or [])
    if clip not in includes:
        includes.append(clip)
    if args.entry_point and args.entry_point not in includes:
        includes.append(args.entry_point)
    if args.package_lock and args.package_lock not in includes:
        includes.append(args.package_lock)
    input_props: Any = None
    if args.input_props:
        props_path, _ = project_relative(root, args.input_props, must_exist=True)
        input_props = json.loads(props_path.read_text(encoding='utf-8'))
        includes.append(args.input_props)
    payload: dict[str, Any] = {
        'schema_version': 1,
        'clip': clip,
        'composition_id': args.composition_id,
        'entry_point': args.entry_point,
        'input_props': input_props,
        'render_command': args.render_command,
        'files': collect_files(root, includes),
    }
    payload['bundle_digest'] = bundle_digest(payload)
    output, relative = project_relative(root, args.output, must_exist=False)
    write_json(output, payload)
    print(json.dumps({'path': relative, 'bundle_digest': payload['bundle_digest'], 'file_count': len(payload['files'])}, indent=2))


def verify_command(args: argparse.Namespace) -> None:
    root = Path(args.project).expanduser().resolve(strict=True)
    path, relative = project_relative(root, args.recipe, must_exist=True)
    payload = verify(root, path)
    print(json.dumps({'path': relative, 'bundle_digest': payload['bundle_digest'], 'verified': True}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description='Create or verify a hash-locked Remotion render recipe.')
    sub = parser.add_subparsers(dest='command', required=True)
    create_parser = sub.add_parser('create')
    create_parser.add_argument('--project', required=True)
    create_parser.add_argument('--clip', required=True)
    create_parser.add_argument('--composition-id', required=True)
    create_parser.add_argument('--entry-point')
    create_parser.add_argument('--input-props')
    create_parser.add_argument('--package-lock')
    create_parser.add_argument('--render-command', required=True)
    create_parser.add_argument('--include', action='append', default=[])
    create_parser.add_argument('--output', required=True)
    create_parser.set_defaults(func=create)

    verify_parser = sub.add_parser('verify')
    verify_parser.add_argument('--project', required=True)
    verify_parser.add_argument('--recipe', required=True)
    verify_parser.set_defaults(func=verify_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
