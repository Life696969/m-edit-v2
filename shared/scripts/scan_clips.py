#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import natural_key, read_json, sha256, write_json

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi', '.mts', '.m2ts'}
BASE_IGNORE = {'.git', '.m-edit', '.m-edit-suite', 'node_modules', 'dist', 'build', '.cache', '__pycache__'}
PROTOCOLS = 'file,pipe,crypto,data'


def probe(path: Path, timeout_seconds: int) -> dict[str, Any]:
    command = [
        'ffprobe', '-protocol_whitelist', PROTOCOLS,
        '-v', 'error', '-show_entries',
        'format=duration,format_name,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt,sample_rate,channels,channel_layout',
        '-of', 'json', str(path),
    ]
    try:
        completed = subprocess.run(command, check=True, text=True, capture_output=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f'ffprobe timed out for {path}') from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or 'unknown ffprobe error'
        raise SystemExit(f'ffprobe failed for {path}: {detail}') from exc
    return json.loads(completed.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description='Create a deterministic inventory of source video clips.')
    parser.add_argument('--project', required=True)
    parser.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args()

    if not shutil.which('ffprobe'):
        raise SystemExit('ffprobe is required')

    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f'Missing project folder: {root}')

    config_path = root / '.m-edit' / 'config.json'
    config = read_json(config_path) if config_path.exists() else {}
    hash_mode = config.get('source_hash_mode', 'full')
    if hash_mode not in {'full', 'stat'}:
        raise SystemExit('source_hash_mode must be "full" or "stat"')

    ignore = set(BASE_IGNORE)
    output_root = config.get('output_root')
    if isinstance(output_root, str) and output_root:
        output_first = Path(output_root).parts[0]
        if output_first not in {'.', '..'}:
            ignore.add(output_first)

    discovered: list[Path] = []
    for path in root.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        relative = path.relative_to(root)
        if any(part in ignore for part in relative.parts[:-1]):
            continue
        discovered.append(path)
    discovered.sort(key=lambda item: natural_key(item.relative_to(root).as_posix()))

    clips = []
    for path in discovered:
        relative = path.relative_to(root).as_posix()
        stat = path.stat()
        clips.append({
            'path': relative,
            'fingerprint': {
                'size_bytes': stat.st_size,
                'mtime_ns': stat.st_mtime_ns,
                'sha256': sha256(path) if hash_mode == 'full' else None,
                'hash_mode': hash_mode,
            },
            'metadata': probe(path, args.timeout),
        })

    output = root / '.m-edit' / 'clip_inventory.json'
    write_json(output, {
        'schema_version': 2,
        'project_root': str(root),
        'hash_mode': hash_mode,
        'clip_count': len(clips),
        'clips': clips,
    })
    print(f'{len(clips)} clips -> {output}')
    if hash_mode == 'stat':
        print('WARNING: stat hash mode is faster but cannot detect same-size, same-mtime content replacement.')


if __name__ == '__main__':
    main()
