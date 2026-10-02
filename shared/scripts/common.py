#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest_json(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode('utf-8')).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise SystemExit(f'Missing JSON file: {path}') from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f'Invalid JSON in {path}: {exc}') from exc
    if not isinstance(value, dict):
        raise SystemExit(f'Expected a JSON object in {path}')
    return value


def write_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def append_jsonl(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(data, ensure_ascii=False) + '\n'
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def project_lock(control: Path, timeout_seconds: float = 15.0) -> Iterator[None]:
    """Portable best-effort lock using atomic lock-file creation.

    The lock contains PID and timestamp. Locks older than 10 minutes are treated as stale.
    """
    control.mkdir(parents=True, exist_ok=True)
    lock = control / 'state.lock'
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                stream.write(json.dumps({'pid': os.getpid(), 'created_at': now()}))
            break
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
                if age > 600:
                    lock.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise SystemExit(f'Timed out waiting for project state lock: {lock}')
            time.sleep(0.1)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def project_relative(root: Path, value: str, *, must_exist: bool = False) -> tuple[Path, str]:
    candidate = Path(value)
    if candidate.is_absolute():
        raise SystemExit('Absolute project artifact paths are not allowed')
    resolved = (root / candidate).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise SystemExit('Path must remain inside the selected project') from exc
    if must_exist and not resolved.exists():
        raise SystemExit(f'Missing project artifact: {relative.as_posix()}')
    return resolved, relative.as_posix()


def boundary_relative(boundary: Path, path: Path, *, must_exist: bool = True) -> Path:
    resolved = path.resolve(strict=must_exist)
    try:
        resolved.relative_to(boundary.resolve())
    except ValueError as exc:
        raise SystemExit(f'Path escapes trusted boundary: {path}') from exc
    return resolved


def natural_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', value)]


def file_record(root: Path, path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    relative = resolved.relative_to(root.resolve()).as_posix()
    stat = resolved.stat()
    return {
        'path': relative,
        'sha256': sha256(resolved),
        'size_bytes': stat.st_size,
        'mtime_ns': stat.st_mtime_ns,
    }


def hash_records(records: list[dict[str, Any]]) -> str:
    normalized = [
        {'path': record['path'], 'sha256': record['sha256'], 'size_bytes': record.get('size_bytes')}
        for record in records
    ]
    return digest_json(normalized)
