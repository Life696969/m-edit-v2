#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import project_relative, sha256, write_json

PROTOCOLS = 'file,pipe,crypto,data'
SSIM_PATTERN = re.compile(r'All:([0-9.]+)')


def run(command: list[str], timeout: int, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=check, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f'Command timed out after {timeout}s: {command[0]}') from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or 'unknown error'
        raise SystemExit(f'{command[0]} failed: {detail}') from exc


def probe(path: Path, timeout: int) -> dict[str, Any]:
    command = [
        'ffprobe', '-protocol_whitelist', PROTOCOLS, '-v', 'error',
        '-show_entries',
        'format=duration,format_name,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt,sample_rate,channels,channel_layout',
        '-of', 'json', str(path),
    ]
    return json.loads(run(command, timeout).stdout)


def first_video(payload: dict[str, Any]) -> dict[str, Any]:
    streams = [stream for stream in payload.get('streams', []) if stream.get('codec_type') == 'video']
    if not streams:
        raise SystemExit('No video stream')
    return streams[0]


def duration(payload: dict[str, Any]) -> float:
    value = float(payload.get('format', {}).get('duration') or 0)
    if value <= 0:
        raise SystemExit('Duration must be greater than zero')
    return value


def compare_media(final: Path, preview: Path, final_probe: dict[str, Any], preview_probe: dict[str, Any],
                  timeout: int, min_ssim: float, max_duration_delta: float) -> dict[str, Any]:
    final_duration = duration(final_probe)
    preview_duration = duration(preview_probe)
    delta = abs(final_duration - preview_duration)
    if delta > max_duration_delta:
        raise SystemExit(f'Final/preview duration mismatch: {delta:.3f}s > {max_duration_delta:.3f}s')
    preview_video = first_video(preview_probe)
    width = int(preview_video['width'])
    height = int(preview_video['height'])
    # A final may be delivered at a higher frame rate than its preview (e.g. 60 vs 30 fps): resample it to the
    # preview's rate first so SSIM compares the same instants, not the same frame numbers.
    rate = preview_video.get('avg_frame_rate') or preview_video.get('r_frame_rate') or ''
    fps = f'fps={rate},' if re.fullmatch(r'\d+/\d+|\d+(\.\d+)?', str(rate)) and not str(rate).startswith('0') else ''
    command = [
        'ffmpeg', '-protocol_whitelist', PROTOCOLS, '-v', 'info',
        '-i', str(final), '-i', str(preview),
        '-filter_complex',
        f'[0:v]{fps}scale={width}:{height}:flags=bicubic,setpts=PTS-STARTPTS[a];'
        '[1:v]setpts=PTS-STARTPTS[b];[a][b]ssim',
        '-an', '-shortest', '-f', 'null', '-',
    ]
    completed = run(command, timeout, check=False)
    match = SSIM_PATTERN.search(completed.stderr)
    if completed.returncode != 0 or not match:
        detail = completed.stderr.strip()[-2000:]
        raise SystemExit(f'Unable to compare final with preview: {detail}')
    score = float(match.group(1))
    if score < min_ssim:
        raise SystemExit(f'Final differs from approved preview: SSIM {score:.6f} < {min_ssim:.6f}')
    return {
        'preview_path': str(preview),
        'preview_sha256': sha256(preview),
        'preview_duration_seconds': preview_duration,
        'final_duration_seconds': final_duration,
        'duration_delta_seconds': delta,
        'ssim': score,
        'minimum_ssim': min_ssim,
        'passed': True,
    }


def contact_sheet(media: Path, output: Path, media_duration: float, timeout: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    interval = max(media_duration / 6.0, 0.05)
    command = [
        'ffmpeg', '-y', '-protocol_whitelist', PROTOCOLS, '-v', 'error',
        '-i', str(media), '-vf',
        f'fps=1/{interval:.6f},scale=320:-2:flags=lanczos,tile=3x2:padding=8:margin=8',
        '-frames:v', '1', str(output),
    ]
    run(command, timeout)


def main() -> None:
    parser = argparse.ArgumentParser(description='Decode, inspect, and optionally compare a rendered video.')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--width', type=int)
    parser.add_argument('--height', type=int)
    parser.add_argument('--require-audio', action='store_true')
    parser.add_argument('--compare-preview')
    parser.add_argument('--min-ssim', type=float, default=0.95)
    parser.add_argument('--max-duration-delta', type=float, default=0.15)
    parser.add_argument('--contact-sheet')
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()

    if not shutil.which('ffprobe') or not shutil.which('ffmpeg'):
        raise SystemExit('ffprobe and ffmpeg are required')

    media = Path(args.input).expanduser().resolve()
    if not media.exists() or media.stat().st_size == 0:
        raise SystemExit('Missing or empty media')

    media_probe = probe(media, args.timeout)
    video = first_video(media_probe)
    media_duration = duration(media_probe)
    audio_streams = [stream for stream in media_probe.get('streams', []) if stream.get('codec_type') == 'audio']
    if args.width and video.get('width') != args.width:
        raise SystemExit(f'Unexpected width {video.get("width")}')
    if args.height and video.get('height') != args.height:
        raise SystemExit(f'Unexpected height {video.get("height")}')
    if args.require_audio and not audio_streams:
        raise SystemExit('Required audio stream is missing')

    decode_command = [
        'ffmpeg', '-protocol_whitelist', PROTOCOLS, '-v', 'error',
        '-i', str(media), '-map', '0', '-f', 'null', '-',
    ]
    decode = run(decode_command, args.timeout, check=False)
    if decode.returncode != 0:
        raise SystemExit(f'Media decode failed: {decode.stderr.strip()}')

    comparison = None
    if args.compare_preview:
        preview = Path(args.compare_preview).expanduser().resolve()
        if not preview.exists():
            raise SystemExit(f'Missing approved preview: {preview}')
        comparison = compare_media(
            media,
            preview,
            media_probe,
            probe(preview, args.timeout),
            args.timeout,
            args.min_ssim,
            args.max_duration_delta,
        )

    if args.contact_sheet:
        sheet = Path(args.contact_sheet).expanduser().resolve()
        contact_sheet(media, sheet, media_duration, args.timeout)

    payload: dict[str, Any] = {
        'schema_version': 2,
        'passed': True,
        'path': str(media),
        'sha256': sha256(media),
        'size_bytes': media.stat().st_size,
        'probe': media_probe,
        'checks': {
            'video_stream': True,
            'audio_stream': bool(audio_streams),
            'duration_positive': True,
            'all_streams_decode': True,
            'expected_width': args.width,
            'expected_height': args.height,
            'contact_sheet': str(Path(args.contact_sheet).expanduser().resolve()) if args.contact_sheet else None,
        },
    }
    if comparison:
        payload['comparison'] = comparison
    output = Path(args.output).expanduser().resolve()
    write_json(output, payload)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
