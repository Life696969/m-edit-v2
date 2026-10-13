#!/usr/bin/env python3
"""Structural MP4 scrub and box inspection for clean final delivery (standard library only).

Removing text tags is not enough: FFmpeg and Remotion also leave structural fingerprints in the MP4 boxes.
`scrub()` fixes them without touching a single video or audio sample:

* `ftyp`: FFmpeg's `isom`/512/`isomiso2avc1mp41` brands become the generic `mp42`/0/`isom mp42`.
* `moov/udta`, `meta`: metadata boxes (for example an empty iTunes `meta/hdlr mdirappl/ilst`) are removed.
* `free`, `skip`, `uuid`: padding and vendor boxes at the top level are removed.
* `colr`: an ICC profile (`prof`, typically from a headless browser) or no box at all becomes `nclx` from the
  stream's own colour description (VUI).
* `btrt`: FFmpeg's bitrate boxes are removed.
* `esds`: FFmpeg's 4-byte descriptor sizes (`80 80 80 xx`) become 1-byte sizes with identical contents.
* `mvhd`/`tkhd`/`mdhd`: zeroed creation/modification times (bit-exact muxing) become the time the file is written.

`stco`/`co64` chunk offsets are shifted by the size change in front of `mdat`. Nothing is ever forged: camera,
date and provenance metadata are only removed, never invented.

    python mp4_scrub.py <in.mp4> <out.mp4> <primaries> <transfer> <matrix> <full_range 0|1>
    python mp4_scrub.py --tree <file.mp4>
"""
from __future__ import annotations

import struct
import sys
import time
from typing import Iterator

CONTAINERS = {b'moov', b'trak', b'mdia', b'minf', b'stbl', b'dinf', b'edts', b'udta', b'mvex'}
MAC_EPOCH = 2082844800                       # seconds from 1904-01-01 to 1970-01-01
DROP_TOP = {b'free', b'skip', b'uuid'}
DROP_IN_MOOV = {b'udta', b'meta'}
DROP_ANYWHERE = {b'btrt'}


class Box:
    def __init__(self, typ: bytes, payload=b'', children: list[Box] | None = None, prefix: bytes = b''):
        self.typ, self.payload, self.children, self.prefix = typ, payload, children, prefix

    def serialize(self) -> bytes:
        body = self.payload if self.children is None else self.prefix + b''.join(c.serialize() for c in self.children)
        size = 8 + len(body)
        if size > 0xFFFFFFFF:
            return struct.pack('>I4sQ', 1, self.typ, size + 8) + body
        return struct.pack('>I4s', size, self.typ) + body


def parse(buf: bytes, start: int, end: int, sample_entry: bool = False) -> list[Box]:
    out = []
    pos = start
    while pos + 8 <= end:
        size, typ = struct.unpack('>I4s', buf[pos:pos + 8])
        header = 8
        if size == 1:
            size = struct.unpack('>Q', buf[pos + 8:pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        s, e = pos + header, pos + size
        if typ == b'mdat':
            out.append(Box(typ, payload=(pos, s, e)))             # kept by reference: (box start, payload start, end)
        elif typ in CONTAINERS:
            out.append(Box(typ, children=parse(buf, s, e)))
        elif typ == b'stsd':
            out.append(Box(typ, prefix=buf[s:s + 8], children=parse(buf, s + 8, e, True)))
        elif sample_entry and typ in (b'avc1', b'avc3', b'hvc1', b'hev1', b'mp4a'):
            fixed = 28 if typ == b'mp4a' else 78                   # AudioSampleEntry / VisualSampleEntry fixed fields
            out.append(Box(typ, prefix=buf[s:s + fixed], children=parse(buf, s + fixed, e)))
        else:
            out.append(Box(typ, payload=buf[s:e]))
        pos += size
    return out


def walk(boxes: list[Box], path: tuple[bytes, ...] = ()) -> Iterator[tuple[tuple[bytes, ...], Box]]:
    for box in boxes:
        yield path + (box.typ,), box
        if box.children:
            yield from walk(box.children, path + (box.typ,))


def read_tree(path) -> tuple[bytes, list[Box]]:
    with open(path, 'rb') as handle:
        buf = handle.read()
    return buf, parse(buf, 0, len(buf))


def _read_descriptor(data: bytes, i: int) -> tuple[int, bytes, int, int]:
    tag = data[i]
    i += 1
    size = 0
    width = 0
    while True:
        byte = data[i]
        i += 1
        width += 1
        size = (size << 7) | (byte & 0x7F)
        if not byte & 0x80:
            break
    return tag, data[i:i + size], i + size, width


def esds_is_short(payload: bytes) -> bool:
    data = payload[4:]
    _, es, _, width = _read_descriptor(data, 0)
    if width != 1:
        return False
    rest, i = es[3:], 0
    while i < len(rest):
        tag, body, i, width = _read_descriptor(rest, i)
        if width != 1:
            return False
        if tag == 0x04:
            sub, j = body[13:], 0
            while j < len(sub):
                _, _, j, sub_width = _read_descriptor(sub, j)
                if sub_width != 1:
                    return False
    return True


def short_esds(payload: bytes) -> bytes:
    """Re-emit the MPEG-4 descriptors with 1-byte sizes (identical contents)."""
    def emit(tag: int, body: bytes) -> bytes:
        if len(body) >= 128:
            raise ValueError('descriptor too long for a 1-byte size')
        return bytes([tag, len(body)]) + body

    head, data = payload[:4], payload[4:]
    tag, es, _, _ = _read_descriptor(data, 0)
    if tag != 0x03:
        raise ValueError('esds does not start with an ES descriptor')
    fixed, rest = es[:3], es[3:]
    if fixed[2] & 0xE0:
        raise ValueError('unexpected ES flags (stream dependence / URL / OCR)')
    inner, i = b'', 0
    while i < len(rest):
        tag, body, i, _ = _read_descriptor(rest, i)
        if tag == 0x04:                                            # DecoderConfigDescriptor holds DecSpecificInfo
            config, sub, j, subs = body[:13], body[13:], 0, b''
            while j < len(sub):
                sub_tag, sub_body, j, _ = _read_descriptor(sub, j)
                subs += emit(sub_tag, sub_body)
            body = config + subs
        inner += emit(tag, body)
    return head + emit(0x03, fixed + inner)


def _set_times(payload: bytes, when: int) -> bytes:
    if payload[0] == 0:
        return payload[:4] + struct.pack('>II', when, when) + payload[12:]
    return payload[:4] + struct.pack('>QQ', when, when) + payload[20:]


def scrub(src, dst, primaries: int, transfer: int, matrix: int, full_range: int) -> int:
    """Write a scrubbed copy of a faststart MP4. Returns the size change in front of mdat (bytes)."""
    buf, top = read_tree(src)
    names = [b.typ for b in top]
    if not (b'moov' in names and b'mdat' in names and names.index(b'moov') < names.index(b'mdat')):
        raise ValueError('expects a faststart file (moov before mdat)')
    old_mdat_at = top[names.index(b'mdat')].payload[0]
    when = int(time.time()) + MAC_EPOCH
    top = [b for b in top if b.typ not in DROP_TOP]
    for box in top:
        if box.typ == b'ftyp':
            box.payload = b'mp42' + struct.pack('>I', 0) + b'isommp42'
        if box.typ == b'moov':
            box.children = [c for c in box.children if c.typ not in DROP_IN_MOOV]
    for _, box in walk(top):
        if box.typ in (b'mvhd', b'tkhd', b'mdhd'):
            box.payload = _set_times(box.payload, when)
        if box.children is None:
            continue
        box.children = [c for c in box.children if c.typ not in DROP_ANYWHERE]
        if box.typ in (b'avc1', b'avc3', b'hvc1', b'hev1'):
            nclx = Box(b'colr', payload=b'nclx' + struct.pack('>HHHB', primaries, transfer, matrix, 0x80 if full_range else 0))
            if any(c.typ == b'colr' for c in box.children):
                box.children = [nclx if c.typ == b'colr' else c for c in box.children]
            else:                                                  # standard order: after avcC/hvcC
                k = next((i + 1 for i, c in enumerate(box.children) if c.typ in (b'avcC', b'hvcC')), len(box.children))
                box.children.insert(k, nclx)
        for child in box.children:
            if child.typ == b'esds':
                child.payload = short_esds(child.payload)

    def head_len() -> int:
        return sum(len(b.serialize()) for b in top[:[x.typ for x in top].index(b'mdat')])

    delta = head_len() - old_mdat_at                               # offset rewrites keep their size: one pass is enough
    for _, box in walk(top):
        if box.typ in (b'stco', b'co64'):
            flags, count = box.payload[:4], struct.unpack('>I', box.payload[4:8])[0]
            fmt, width = ('>I', 4) if box.typ == b'stco' else ('>Q', 8)
            values = [struct.unpack(fmt, box.payload[8 + i * width:8 + (i + 1) * width])[0] + delta for i in range(count)]
            box.payload = flags + struct.pack('>I', count) + b''.join(struct.pack(fmt, v) for v in values)
    if head_len() - old_mdat_at != delta:
        raise RuntimeError('chunk-offset rewrite changed the header size')
    with open(dst, 'wb') as handle:
        for box in top:
            if box.typ == b'mdat':
                start, _, end = box.payload
                handle.write(buf[start:end])
            else:
                handle.write(box.serialize())
    return delta


def describe(path) -> list[tuple[tuple[bytes, ...], bytes, bytes | None]]:
    """(path, type, payload or None) for every box, for checks and --tree."""
    _, top = read_tree(path)
    return [(p, b.typ, None if b.typ == b'mdat' or b.children is not None else b.payload) for p, b in walk(top)]


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == '--tree':
        for path, typ, payload in describe(sys.argv[2]):
            print('  ' * (len(path) - 1) + typ.decode('latin1'), '' if payload is None else repr(payload[:48]))
    elif len(sys.argv) == 7:
        delta = scrub(sys.argv[1], sys.argv[2], *(int(x) for x in sys.argv[3:7]))
        print(f'scrubbed {sys.argv[1]} -> {sys.argv[2]} (head {delta:+d} bytes)')
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
