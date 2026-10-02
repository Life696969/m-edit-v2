#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import read_json, write_json

TIMESTAMP = re.compile(r'(?:(?P<h>\d{1,2}):)?(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})')
RANGE = re.compile(r'(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}[,.]\d{3})')


def to_ms(value: str) -> int:
    match = TIMESTAMP.fullmatch(value.strip())
    if not match:
        raise SystemExit(f'Invalid caption timestamp: {value}')
    return (
        int(match.group('h') or 0) * 3_600_000
        + int(match.group('m')) * 60_000
        + int(match.group('s')) * 1_000
        + int(match.group('ms'))
    )


def from_ms(value: int, separator: str = ',') -> str:
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{milliseconds:03d}'


def parse_srt_vtt(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n').split('\n')
    segments: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        match = RANGE.search(line)
        if not match:
            index += 1
            continue
        start = to_ms(match.group('start'))
        end = to_ms(match.group('end'))
        index += 1
        text_lines = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        text = ' '.join(text_lines).strip()
        if text:
            segments.append({'start_ms': start, 'end_ms': end, 'text': text})
    return segments


def parse_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(payload, dict) and isinstance(payload.get('segments'), list):
        source = payload['segments']
    elif isinstance(payload, list):
        source = payload
    else:
        raise SystemExit('Unsupported caption JSON: expected a segments array or top-level array')
    segments = []
    for item in source:
        if not isinstance(item, dict):
            continue
        start = item.get('start_ms')
        end = item.get('end_ms')
        if start is None and item.get('start') is not None:
            start = round(float(item['start']) * 1000)
        if end is None and item.get('end') is not None:
            end = round(float(item['end']) * 1000)
        text = str(item.get('text') or '').strip()
        if start is None or end is None:
            raise SystemExit('Caption JSON segment is missing start/end timing')
        segments.append({
            'start_ms': int(start),
            'end_ms': int(end),
            'text': text,
            **({'confidence': item['confidence']} if item.get('confidence') is not None else {}),
            **({'words': item['words']} if isinstance(item.get('words'), list) else {}),
        })
    return segments


def validate_segments(segments: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    previous_start = -1
    for index, segment in enumerate(segments, 1):
        start = segment.get('start_ms')
        end = segment.get('end_ms')
        text = segment.get('text')
        if not isinstance(start, int) or start < 0:
            errors.append(f'segment {index}: start_ms must be a non-negative integer')
        if not isinstance(end, int) or not isinstance(start, int) or end <= start:
            errors.append(f'segment {index}: end_ms must be greater than start_ms')
        if not isinstance(text, str) or not text.strip():
            errors.append(f'segment {index}: text is empty')
        if isinstance(start, int) and start < previous_start:
            errors.append(f'segment {index}: timestamps are not sorted')
        if isinstance(start, int):
            previous_start = start
    return errors


def canonical_payload(source: Path, segments: list[dict[str, Any]]) -> dict[str, Any]:
    errors = validate_segments(segments)
    if errors:
        raise SystemExit('\n'.join(errors))
    return {
        'schema_version': 1,
        'source': str(source),
        'language': None,
        'segments': segments,
    }


def import_command(args: argparse.Namespace) -> None:
    source = Path(args.input).expanduser().resolve(strict=True)
    if source.suffix.lower() in {'.srt', '.vtt'}:
        segments = parse_srt_vtt(source)
    elif source.suffix.lower() == '.json':
        segments = parse_json(source)
    else:
        raise SystemExit('Supported inputs: .srt, .vtt, .json')
    payload = canonical_payload(source, segments)
    write_json(Path(args.output).expanduser().resolve(), payload)
    print(f'{len(segments)} segments -> {args.output}')


def validate_command(args: argparse.Namespace) -> None:
    payload = read_json(Path(args.input).expanduser().resolve(strict=True))
    segments = payload.get('segments')
    if not isinstance(segments, list):
        raise SystemExit('Caption JSON is missing a segments array')
    errors = validate_segments(segments)
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'valid: {len(segments)} segments')


def export_srt(args: argparse.Namespace) -> None:
    payload = read_json(Path(args.input).expanduser().resolve(strict=True))
    segments = payload.get('segments')
    if not isinstance(segments, list):
        raise SystemExit('Caption JSON is missing a segments array')
    errors = validate_segments(segments)
    if errors:
        raise SystemExit('\n'.join(errors))
    lines = []
    for index, segment in enumerate(segments, 1):
        lines.extend([
            str(index),
            f'{from_ms(segment["start_ms"])} --> {from_ms(segment["end_ms"])}',
            segment['text'],
            '',
        ])
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')
    print(output)



def group_tokens(tokens: list[str], max_words: int, max_chars: int) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        proposed = ' '.join([*current, token])
        if current and (len(current) >= max_words or len(proposed) > max_chars):
            groups.append(current)
            current = [token]
        else:
            current.append(token)
    if current:
        groups.append(current)
    return groups


def chunk_segment(segment: dict[str, Any], max_words: int, max_chars: int) -> list[dict[str, Any]]:
    words = segment.get('words')
    if isinstance(words, list) and words and all(isinstance(word, dict) for word in words):
        normalized = []
        for word in words:
            text = str(word.get('text') or word.get('word') or '').strip()
            start = word.get('start_ms')
            end = word.get('end_ms')
            if start is None and word.get('start') is not None:
                start = round(float(word['start']) * 1000)
            if end is None and word.get('end') is not None:
                end = round(float(word['end']) * 1000)
            if text and isinstance(start, int) and isinstance(end, int) and end > start:
                normalized.append({'text': text, 'start_ms': start, 'end_ms': end})
        if normalized:
            chunks: list[dict[str, Any]] = []
            current: list[dict[str, Any]] = []
            for word in normalized:
                proposed = ' '.join([*(item['text'] for item in current), word['text']])
                if current and (len(current) >= max_words or len(proposed) > max_chars):
                    chunks.append({
                        'start_ms': current[0]['start_ms'],
                        'end_ms': current[-1]['end_ms'],
                        'text': ' '.join(item['text'] for item in current),
                    })
                    current = [word]
                else:
                    current.append(word)
            if current:
                chunks.append({
                    'start_ms': current[0]['start_ms'],
                    'end_ms': current[-1]['end_ms'],
                    'text': ' '.join(item['text'] for item in current),
                })
            return chunks

    tokens = str(segment['text']).split()
    groups = group_tokens(tokens, max_words, max_chars)
    if len(groups) <= 1:
        return [{'start_ms': segment['start_ms'], 'end_ms': segment['end_ms'], 'text': segment['text'].strip()}]
    start = int(segment['start_ms'])
    end = int(segment['end_ms'])
    duration = end - start
    weights = [max(1, len(' '.join(group))) for group in groups]
    total = sum(weights)
    cursor = start
    output = []
    for index, (group, weight) in enumerate(zip(groups, weights)):
        chunk_end = end if index == len(groups) - 1 else cursor + round(duration * weight / total)
        if chunk_end <= cursor:
            chunk_end = min(end, cursor + 1)
        output.append({'start_ms': cursor, 'end_ms': chunk_end, 'text': ' '.join(group)})
        cursor = chunk_end
    return output


def chunk_command(args: argparse.Namespace) -> None:
    source = Path(args.input).expanduser().resolve(strict=True)
    payload = read_json(source)
    segments = payload.get('segments')
    if not isinstance(segments, list):
        raise SystemExit('Caption JSON is missing a segments array')
    errors = validate_segments(segments)
    if errors:
        raise SystemExit('\n'.join(errors))
    chunked = []
    for segment in segments:
        chunked.extend(chunk_segment(segment, args.max_words, args.max_chars))
    output_payload = dict(payload)
    output_payload['segments'] = chunked
    output_payload['chunking'] = {'max_words': args.max_words, 'max_chars': args.max_chars}
    errors = validate_segments(chunked)
    if errors:
        raise SystemExit('\n'.join(errors))
    write_json(Path(args.output).expanduser().resolve(), output_payload)
    print(f'{len(segments)} segments -> {len(chunked)} caption chunks')

def main() -> None:
    parser = argparse.ArgumentParser(description='Import, validate, and export canonical caption data.')
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('import')
    command.add_argument('--input', required=True)
    command.add_argument('--output', required=True)
    command.set_defaults(func=import_command)
    command = sub.add_parser('validate')
    command.add_argument('--input', required=True)
    command.set_defaults(func=validate_command)
    command = sub.add_parser('export-srt')
    command.add_argument('--input', required=True)
    command.add_argument('--output', required=True)
    command.set_defaults(func=export_srt)
    command = sub.add_parser('chunk')
    command.add_argument('--input', required=True)
    command.add_argument('--output', required=True)
    command.add_argument('--max-words', type=int, default=4)
    command.add_argument('--max-chars', type=int, default=32)
    command.set_defaults(func=chunk_command)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
