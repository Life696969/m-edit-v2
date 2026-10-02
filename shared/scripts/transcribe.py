#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from captions import canonical_payload, parse_json, parse_srt_vtt
from common import project_relative, read_json, write_json


def available_providers() -> dict[str, bool]:
    return {
        'existing': True,
        'openai-whisper': bool(shutil.which('whisper')),
        'faster-whisper': importlib.util.find_spec('faster_whisper') is not None,
        'whisper-cpp': bool(shutil.which('whisper-cli') or shutil.which('main')),
        'host': True,
    }


def choose_existing(root: Path, clip: Path, globs: list[str]) -> Path | None:
    candidates: list[Path] = []
    for pattern in globs:
        for path in clip.parent.glob(pattern):
            if path.is_file() and path.stem == clip.stem:
                candidates.append(path)
    preference = {'.json': 0, '.srt': 1, '.vtt': 2}
    candidates.sort(key=lambda path: (preference.get(path.suffix.lower(), 99), path.name))
    return candidates[0] if candidates else None


def import_existing(path: Path) -> dict[str, Any]:
    if path.suffix.lower() in {'.srt', '.vtt'}:
        return canonical_payload(path, parse_srt_vtt(path))
    if path.suffix.lower() == '.json':
        return canonical_payload(path, parse_json(path))
    raise SystemExit(f'Unsupported existing caption file: {path}')



def local_openai_model_available(config: dict[str, Any]) -> bool:
    model_path = config.get('model_path')
    if not model_path:
        return False
    path = Path(str(model_path)).expanduser().resolve()
    if path.is_file() and path.suffix == '.pt':
        return True
    if path.is_dir():
        model = str(config.get('model', 'base'))
        return (path / f'{model}.pt').is_file() or any(path.glob('*.pt'))
    return False

def openai_whisper(clip: Path, config: dict[str, Any], timeout: int, allow_network: bool) -> dict[str, Any]:
    if not shutil.which('whisper'):
        raise SystemExit('OpenAI Whisper CLI is not installed')
    if not local_openai_model_available(config) and not allow_network:
        raise SystemExit('OpenAI Whisper has no confirmed local .pt model. Configure transcription.model_path or explicitly authorize network access.')
    with tempfile.TemporaryDirectory() as temporary:
        command = [
            'whisper', str(clip),
            '--model', str(config.get('model', 'base')),
            '--output_dir', temporary,
            '--output_format', 'json',
            '--word_timestamps', 'True',
            '--verbose', 'False',
        ]
        language = config.get('language')
        if language and language != 'auto':
            command.extend(['--language', str(language)])
        model_path = config.get('model_path')
        if model_path:
            command.extend(['--model_dir', str(Path(model_path).expanduser().resolve())])
        try:
            completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise SystemExit('OpenAI Whisper transcription timed out') from exc
        if completed.returncode != 0:
            raise SystemExit(f'OpenAI Whisper failed: {completed.stderr.strip()}')
        output = Path(temporary) / f'{clip.stem}.json'
        if not output.exists():
            matches = list(Path(temporary).glob('*.json'))
            if len(matches) != 1:
                raise SystemExit('OpenAI Whisper did not produce a usable JSON file')
            output = matches[0]
        payload = canonical_payload(clip, parse_json(output))
        payload['provider'] = 'openai-whisper'
        return payload


def faster_whisper(clip: Path, config: dict[str, Any]) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise SystemExit('faster-whisper is not installed') from exc
    model_value = config.get('model_path') or config.get('model', 'base')
    if not config.get('model_path'):
        raise SystemExit('For network-safe faster-whisper use, set transcription.model_path to a local model directory')
    model = WhisperModel(str(model_value), device='auto', compute_type='auto')
    language = config.get('language')
    segments_iter, info = model.transcribe(
        str(clip),
        language=None if language in {None, 'auto'} else str(language),
        word_timestamps=bool(config.get('word_timestamps', True)),
    )
    segments = []
    for segment in segments_iter:
        words = []
        for word in getattr(segment, 'words', None) or []:
            words.append({
                'start_ms': round(float(word.start) * 1000),
                'end_ms': round(float(word.end) * 1000),
                'text': str(word.word).strip(),
                'confidence': float(word.probability),
            })
        segments.append({
            'start_ms': round(float(segment.start) * 1000),
            'end_ms': round(float(segment.end) * 1000),
            'text': str(segment.text).strip(),
            **({'words': words} if words else {}),
        })
    payload = canonical_payload(clip, segments)
    payload['provider'] = 'faster-whisper'
    payload['language'] = getattr(info, 'language', None)
    return payload


def whisper_cpp(clip: Path, config: dict[str, Any], timeout: int) -> dict[str, Any]:
    binary = shutil.which('whisper-cli') or shutil.which('main')
    model_path = config.get('model_path')
    if not binary or not model_path:
        raise SystemExit('whisper.cpp requires whisper-cli and transcription.model_path')
    if not shutil.which('ffmpeg'):
        raise SystemExit('ffmpeg is required to prepare whisper.cpp audio')
    with tempfile.TemporaryDirectory() as temporary:
        wav = Path(temporary) / 'audio.wav'
        extract = subprocess.run([
            'ffmpeg', '-y', '-v', 'error', '-i', str(clip),
            '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav),
        ], text=True, capture_output=True, timeout=timeout)
        if extract.returncode != 0:
            raise SystemExit(f'Audio extraction failed: {extract.stderr.strip()}')
        prefix = Path(temporary) / 'result'
        command = [binary, '-m', str(Path(model_path).expanduser().resolve()), '-f', str(wav), '-oj', '-of', str(prefix)]
        language = config.get('language')
        if language and language != 'auto':
            command.extend(['-l', str(language)])
        completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        if completed.returncode != 0:
            raise SystemExit(f'whisper.cpp failed: {completed.stderr.strip()}')
        output = prefix.with_suffix('.json')
        if not output.exists():
            raise SystemExit('whisper.cpp did not produce JSON output')
        payload = canonical_payload(clip, parse_json(output))
        payload['provider'] = 'whisper-cpp'
        return payload


def run_command(args: argparse.Namespace) -> None:
    root = Path(args.project).expanduser().resolve(strict=True)
    clip, relative = project_relative(root, args.clip, must_exist=True)
    config = read_json(root / '.m-edit' / 'config.json').get('transcription', {})
    provider = args.provider or config.get('provider', 'auto')
    available = available_providers()
    existing = choose_existing(root, clip, list(config.get('existing_caption_globs', ['*.srt', '*.vtt', '*.json'])))

    if provider == 'auto':
        if existing:
            provider = 'existing'
        elif available['openai-whisper'] and local_openai_model_available(config):
            provider = 'openai-whisper'
        elif available['faster-whisper'] and config.get('model_path'):
            provider = 'faster-whisper'
        elif available['whisper-cpp'] and config.get('model_path'):
            provider = 'whisper-cpp'
        else:
            provider = 'host'

    if provider == 'existing':
        if not existing:
            raise SystemExit(f'No adjacent caption file found for {relative}')
        payload = import_existing(existing)
        payload['provider'] = 'existing'
    elif provider == 'openai-whisper':
        payload = openai_whisper(clip, config, args.timeout, bool(args.allow_network or config.get('allow_network', False)))
    elif provider == 'faster-whisper':
        payload = faster_whisper(clip, config)
    elif provider == 'whisper-cpp':
        payload = whisper_cpp(clip, config, args.timeout)
    elif provider == 'host':
        raise SystemExit(
            'No local transcription provider is available. The host agent must inspect the audio, '
            'or the user must provide an adjacent .srt/.vtt/.json file, install Whisper, or configure a local model.'
        )
    else:
        raise SystemExit(f'Unsupported transcription provider: {provider}')

    payload['clip'] = relative
    output, _ = project_relative(root, args.output, must_exist=False)
    write_json(output, payload)
    print(json.dumps({'provider': provider, 'segments': len(payload['segments']), 'output': str(output)}, indent=2))


def detect_command(_: argparse.Namespace) -> None:
    print(json.dumps(available_providers(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description='Use an existing or optional local Whisper provider to create canonical transcript data.')
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('detect')
    command.set_defaults(func=detect_command)
    command = sub.add_parser('run')
    command.add_argument('--project', required=True)
    command.add_argument('--clip', required=True)
    command.add_argument('--output', required=True)
    command.add_argument('--provider', choices=['auto', 'existing', 'openai-whisper', 'faster-whisper', 'whisper-cpp', 'host'])
    command.add_argument('--timeout', type=int, default=1800)
    command.add_argument('--allow-network', action='store_true', help='Permit a provider to download a model when explicitly requested.')
    command.set_defaults(func=run_command)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
