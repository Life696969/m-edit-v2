#!/usr/bin/env python3
"""Turn `.m-edit/edit.json` into one Remotion props file per clip, for the starter's `ReelClip` composition.

    m-edit edit-props --edit .m-edit/edit.json --clip clip1.mp4 --preset preview --output props/clip1-preview.json

The same edit file feeds the audit and the render, so what was audited is what is rendered. Per clip,
`edit.json` gives `src: {"preview": "...", "final": "..."}` (paths under the Remotion public dir). Music,
when present, is one bed for the whole video; each clip starts it at its own offset, so the separate
final files play continuously in order.
"""
from __future__ import annotations

import argparse
import statistics
from pathlib import Path
from typing import Any

from common import read_json, write_json

DEFAULT_THEME = {
    'font': 'Inter, "Segoe UI", system-ui, sans-serif',
    'textColor': '#FFFFFF',
    'highlightColor': '#FFE14D',
    'captionSize': 68,
    'bigCaptionSize': 86,
    'stage': '#0A0E17',
    'stageGlow': '#2B4F9A66',
    'cardBackground': '#FFFFFF',
}
PRESETS = {'preview': (1080, 1920, 30), 'final': (2160, 3840, 60)}


def face_geom(clip: dict[str, Any]) -> dict[str, float]:
    if clip.get('geom'):
        return clip['geom']
    rows = [r for r in clip.get('face') or [] if {'eye', 'chin'} <= r.keys()]
    if not rows:
        return {'cx': 0.5, 'cy': 0.36, 'h': 0.45}
    chin = statistics.median(r['chin'] for r in rows)
    top = statistics.median(r.get('top', 2 * r['eye'] - r['chin']) for r in rows)
    cx = statistics.median(r.get('cx', 0.5) for r in rows)
    return {'cx': round(cx, 4), 'cy': round((top + chin) / 2, 4), 'h': round(chin - top, 4)}


def build(edit: dict[str, Any], clip_id: str, preset: str) -> dict[str, Any]:
    clips = edit.get('clips') or []
    index = next((i for i, c in enumerate(clips) if c.get('id') == clip_id), None)
    if index is None:
        raise SystemExit(f'{clip_id} is not in edit.json')
    clip = clips[index]
    assets = {a['id']: a for a in edit.get('assets') or []}
    width, height, fps = PRESETS[preset]
    canvas = edit.get('canvas') or {}
    if preset == 'preview':
        width, height, fps = canvas.get('width', width), canvas.get('height', height), canvas.get('fps', fps)
    src = clip.get('src') or {}
    if preset not in src:
        raise SystemExit(f'{clip_id}: edit.json needs src.{preset} (footage path under the Remotion public dir)')
    offset = sum(float(c['duration']) for c in clips[:index])
    music = edit.get('music')
    bed = None
    if music:
        asset = assets.get(music.get('asset'))
        if not asset:
            raise SystemExit('music.asset is not in the asset ledger')
        bed = {'src': asset.get('public_path', asset['path']), 'from': round(offset + float(music.get('offset', 0)), 4),
               'volume': float(music.get('volume', 1.0))}
    cues = []
    for cue in clip.get('cues') or []:
        asset = assets.get(cue['asset'])
        if not asset:
            raise SystemExit(f'cue sound {cue["asset"]!r} is not in the asset ledger')
        cues.append({'src': asset.get('public_path', asset['path']), 'at': cue['at'], 'volume': float(cue.get('volume', 1.0))})
    return {
        'width': width,
        'height': height,
        'fps': fps,
        'durationSec': float(clip['duration']),
        'src': src[preset],
        'words': clip.get('words') or [],
        'chunks': clip.get('chunks') or [],
        'camera': {'origin': (clip.get('camera') or {}).get('origin', [0.5, 0.36]),
                   'keys': (clip.get('camera') or {}).get('keys', []),
                   'shakes': (clip.get('camera') or {}).get('shakes', [])},
        'layers': clip.get('layers') or [],
        'cues': cues,
        'geom': face_geom(clip),
        **({'bed': bed} if bed else {}),
        'theme': {**DEFAULT_THEME, **(edit.get('theme') or {})},
        'cutawayCaptionY': float(edit.get('cutaway_caption_y', 0.765)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='edit.json -> per-clip ReelClip props')
    parser.add_argument('--edit', required=True)
    parser.add_argument('--clip', required=True)
    parser.add_argument('--preset', choices=sorted(PRESETS), default='preview')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    props = build(read_json(Path(args.edit).expanduser().resolve(strict=True)), args.clip, args.preset)
    write_json(Path(args.output).expanduser().resolve(), props)
    print(args.output)


if __name__ == '__main__':
    main()
