#!/usr/bin/env python3
"""Editing rules as code.

    m-edit camera --duration 6.5 --punch 0.0 2.2 4.2 --jump 3.1 --seed 7      # sine-keyed camera, one key per pulse
    m-edit audit-edit --edit .m-edit/edit.json --output .m-edit/edit_audit.json [--config .m-edit/config.json]

The audit reads the edit-decision data (`edit.json`, see shared/references/edit-data.md) and fails on any
violation of the mechanical rules: camera rhythm and frame-edge exposure, caption coverage and length,
cutaway ceiling and length, clip-bounded layers, background policy, depth mattes, named-people photos,
anchor-hit count, licensed asset ledger, and (when face data is supplied) caption/mouth and card/eye
clearance. A preview cannot be recorded without a passing report for the
current edit file.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
from pathlib import Path
from typing import Any

from common import read_json, sha256, write_json

DEFAULT_RULES: dict[str, Any] = {
    'camera_pulse_seconds': 1.0,
    'camera_scale_min': 1.03,
    'camera_scale_max': 1.075,
    'camera_drift_max': 0.006,
    'camera_min_move': 0.004,
    'edge_margin_px': 8,
    'cutaway_share_max': 0.35,
    'cutaway_max_seconds': 4.5,
    'max_caption_words': 4,
    'max_caption_hold_seconds': 1.9,
    'max_anchor_hits': 1,
    'background': 'preserve',
    'people_require_spoken_name': True,
    'caption_mouth_gap_px': 24,
    'card_eye_clearance_px': 150,
}
LAYER_TYPES = {'cutaway', 'card', 'depth', 'photo', 'logo', 'overlay', 'broll', 'text', 'background-replace'}
FULL_FRAME = {'cutaway', 'broll'}
EPS = 1e-6


# ---------------------------------------------------------------- camera
def ease(u: float) -> float:
    """Sine ease in and out: every move leaves from rest and settles on its key."""
    return 0.5 - 0.5 * math.cos(math.pi * u)


def camera_at(keys: list[dict[str, float]], t: float) -> dict[str, float]:
    if t <= keys[0]['t']:
        return keys[0]
    for a, b in zip(keys, keys[1:]):
        if a['t'] <= t < b['t']:
            e = ease((t - a['t']) / (b['t'] - a['t']))
            return {k: a[k] + (b[k] - a[k]) * e for k in ('s', 'x', 'y')} | {'t': t}
    return keys[-1]


def generate_camera(duration: float, *, rules: dict[str, Any] | None = None, punches: list[float] | None = None,
                    jumps: list[float] | None = None, seed: int = 0, origin: tuple[float, float] = (0.5, 0.36),
                    width: int = 1080, height: int = 1920, shake_px: float = 0.0) -> list[dict[str, float]]:
    """One sine-eased key per pulse (plus punch and jump-cut keys), alternating low/high scale bands so that
    no two consecutive moves are the same size, and translation always inside the crop the scale affords."""
    r = {**DEFAULT_RULES, **(rules or {})}
    pulse, smin, smax = r['camera_pulse_seconds'], r['camera_scale_min'], r['camera_scale_max']
    span = smax - smin
    lo_band = (smin, smin + 0.22 * span)
    hi_band = (smin + 0.40 * span, smin + 0.62 * span)
    rng = random.Random(seed)
    punches = sorted(round(p, 3) for p in (punches or []) if 0 <= p <= duration)
    jumps = sorted(round(j, 3) for j in (jumps or []) if 0 < j < duration)
    n = max(1, math.ceil(duration / pulse - 1e-9))
    times = {round(i * duration / n, 3) for i in range(n + 1)}
    times = {t for t in times if all(abs(t - j) >= 0.12 for j in jumps)}
    for p in punches:                                   # a punch replaces the nearest pulse key when close
        near = [t for t in times if abs(t - p) < 0.12 and t not in (0.0, round(duration, 3))]
        times -= set(near)
        times.add(p)
    pre_jump = {round(j - 1 / 60, 4) for j in jumps}
    times |= set(jumps) | pre_jump | {0.0, round(duration, 4)}
    times = sorted(times)
    # fill any gap the removals opened, so no gap exceeds the pulse
    filled: list[float] = [times[0]]
    for t in times[1:]:
        while t - filled[-1] > pulse + EPS:
            filled.append(round(filled[-1] + pulse * 0.98, 4))
        filled.append(t)
    keys: list[dict[str, float]] = []
    last_s = last_mag = None
    margin = r['edge_margin_px']
    for i, t in enumerate(filled):
        for _ in range(500):
            if t in punches:
                s = smax - rng.uniform(0, 0.08 * span)
            elif t in jumps:
                s = rng.uniform(*lo_band) if (last_s or smin) > (smin + smax) / 2 else rng.uniform(*hi_band)
            else:
                s = rng.uniform(*(lo_band if i % 2 == 0 else hi_band))
            if t in pre_jump and keys:
                s = keys[-1]['s'] + (0.3 * span if keys[-1]['s'] < (smin + smax) / 2 else -0.3 * span)
                break
            if last_s is None:
                break
            mag = abs(s - last_s)
            if mag >= r['camera_min_move'] and (last_mag is None or abs(mag - last_mag) > 0.002):
                break
        s = round(min(max(s, smin), smax), 4)
        xmax, ymax = drift_limits(s, r, origin, width, height, shake_px)
        x = rng.uniform(-xmax, xmax)
        if keys and abs(x - keys[-1]['x']) < 0.001:
            x = -x
        y = rng.uniform(-ymax, ymax)
        keys.append({'t': round(t, 4), 's': s, 'x': toward_zero(x), 'y': toward_zero(y)})
        last_mag = None if last_s is None else abs(s - last_s)
        last_s = s
    return repair_metronome(keys, r, origin, width, height, shake_px)


def toward_zero(v: float) -> float:
    return math.copysign(math.floor(abs(v) * 1e4) / 1e4, v)


def drift_limits(s: float, r: dict[str, Any], origin: tuple[float, float], width: int, height: int,
                 shake_px: float) -> tuple[float, float]:
    """How far the frame may drift at scale s without exposing an edge (1 px of rounding headroom)."""
    pad = r['edge_margin_px'] + shake_px + 1.0
    xmax = max(0.0, min(r['camera_drift_max'], (s - 1) * 0.5 - pad / width))
    ymax = max(0.0, min(r['camera_drift_max'], (s - 1) * origin[1] - pad / height, (s - 1) * (1 - origin[1]) - pad / height))
    return xmax, ymax


def repair_metronome(keys: list[dict[str, float]], r: dict[str, Any], origin: tuple[float, float], width: int,
                     height: int, shake_px: float) -> list[dict[str, float]]:
    """Nudge a key whenever two consecutive pulse moves come out the same size."""
    smin, smax = r['camera_scale_min'], r['camera_scale_max']
    for _ in range(400):
        changed = False
        moves = [(i, abs(keys[i + 1]['s'] - keys[i]['s'])) for i in range(len(keys) - 1) if keys[i + 1]['t'] - keys[i]['t'] >= 0.1]
        for (i0, m0), (i1, m1) in zip(moves, moves[1:]):
            if abs(m0 - m1) < 0.0005 or m1 < r['camera_min_move']:
                k, prev = keys[i1 + 1], keys[i1]
                away = 0.003 if k['s'] >= prev['s'] else -0.003       # grow this move...
                if not smin <= k['s'] + away <= smax:
                    away = -away                                       # ...or shrink it when there is no room
                k['s'] = round(min(max(k['s'] + away, smin), smax), 4)
                xmax, ymax = drift_limits(k['s'], r, origin, width, height, shake_px)
                k['x'] = toward_zero(max(-xmax, min(xmax, k['x'])))
                k['y'] = toward_zero(max(-ymax, min(ymax, k['y'])))
                changed = True
                break
        if not changed:
            break
    return keys


# ---------------------------------------------------------------- audit
class Audit:
    def __init__(self, rules: dict[str, Any]):
        self.rules = rules
        self.findings: list[dict[str, Any]] = []

    def fail(self, clip: str | None, rule: str, message: str) -> None:
        self.findings.append({'clip': clip, 'rule': rule, 'message': message})


def audit_camera(a: Audit, cid: str, clip: dict[str, Any], canvas: dict[str, Any]) -> int:
    r = a.rules
    cam = clip.get('camera') or {}
    keys = sorted(cam.get('keys') or [], key=lambda k: k['t'])
    if not keys:
        a.fail(cid, 'camera.keys', 'no camera keys: every clip needs a key on every pulse')
        return 0
    width, height = canvas['width'], canvas['height']
    oy = (cam.get('origin') or [0.5, 0.36])[1]
    shake = max([float(s.get('amp', 0)) for s in cam.get('shakes', [])], default=0.0)
    dur = float(clip['duration'])
    if abs(keys[0]['t']) > 1e-3 or abs(keys[-1]['t'] - dur) > 1e-3:
        a.fail(cid, 'camera.span', f'keys must span 0..{dur:.3f}s (got {keys[0]["t"]}..{keys[-1]["t"]})')
    for k0, k1 in zip(keys, keys[1:]):
        if k1['t'] - k0['t'] > r['camera_pulse_seconds'] + 1e-3:
            a.fail(cid, 'camera.pulse', f'{k1["t"] - k0["t"]:.2f}s without a camera key at {k0["t"]:.2f}s (pulse {r["camera_pulse_seconds"]}s)')
    margin = r['edge_margin_px']
    for k in keys:
        s, x, y = k['s'], k['x'], k['y']
        if s < r['camera_scale_min'] - 1e-4 or s > r['camera_scale_max'] + 1e-4:
            a.fail(cid, 'camera.scale', f't={k["t"]}: scale {s} outside {r["camera_scale_min"]}..{r["camera_scale_max"]}')
        if abs(x) > r['camera_drift_max'] + 1e-4 or abs(y) > r['camera_drift_max'] + 1e-4:
            a.fail(cid, 'camera.drift', f't={k["t"]}: drift beyond {r["camera_drift_max"]} of the frame')
        if abs(x) * width + shake > (s - 1) * 0.5 * width - margin + 1e-6:
            a.fail(cid, 'camera.edge', f't={k["t"]}: horizontal move exposes a frame edge')
        if y * height + shake > (s - 1) * oy * height - margin + 1e-6 or -y * height + shake > (s - 1) * (1 - oy) * height - margin + 1e-6:
            a.fail(cid, 'camera.edge', f't={k["t"]}: vertical move exposes a frame edge')
    moves = []
    for k0, k1 in zip(keys, keys[1:]):
        if k1['t'] - k0['t'] < 0.1:          # jump-cut reframes are instant, not pulses
            moves.append(None)
            continue
        m = abs(k1['s'] - k0['s'])
        moves.append(m)
        if m + abs(k1['x'] - k0['x']) + abs(k1['y'] - k0['y']) < r['camera_min_move'] - 1e-6:
            a.fail(cid, 'camera.felt', f'{k0["t"]:.2f}->{k1["t"]:.2f}s: move too small to be felt')
    for m0, m1 in zip(moves, moves[1:]):
        if m0 is not None and m1 is not None and abs(m0 - m1) < 1e-4:
            a.fail(cid, 'camera.metronome', 'two consecutive camera moves are the same size (reads as a metronome)')
            break
    return len(keys)


def audit_captions(a: Audit, cid: str, clip: dict[str, Any]) -> None:
    r = a.rules
    words = clip.get('words') or []
    chunks = clip.get('chunks') or []
    seen: list[int] = []
    for ci, ch in enumerate(chunks):
        idx = ch.get('words') or []
        if not idx:
            a.fail(cid, 'captions.empty', f'chunk {ci} has no words')
            continue
        if any(not isinstance(i, int) or i < 0 or i >= len(words) for i in idx):
            a.fail(cid, 'captions.index', f'chunk {ci} references a missing word')
            continue
        if idx != list(range(idx[0], idx[-1] + 1)):
            a.fail(cid, 'captions.contiguous', f'chunk {ci} is not a contiguous run of words')
        if len(idx) > r['max_caption_words']:
            a.fail(cid, 'captions.length', f'chunk {ci} shows {len(idx)} words (max {r["max_caption_words"]})')
        if not set(ch.get('hl') or []) <= set(idx):
            a.fail(cid, 'captions.highlight', f'chunk {ci} highlights a word outside itself')
        hold = words[idx[-1]]['e'] - words[idx[0]]['s']
        if hold > r['max_caption_hold_seconds'] + 1e-6:
            a.fail(cid, 'captions.hold', f'chunk {ci} ("{" ".join(words[i]["t"] for i in idx)}") holds {hold:.2f}s')
        seen.extend(idx)
    if sorted(seen) != list(range(len(words))):
        missing = sorted(set(range(len(words))) - set(seen))
        repeated = sorted({i for i in seen if seen.count(i) > 1})
        a.fail(cid, 'captions.coverage', f'every spoken word must be captioned exactly once (missing {missing[:8]}, repeated {repeated[:8]})')
    if seen != sorted(seen):
        a.fail(cid, 'captions.order', 'chunks are out of spoken order')


def spoken(words: list[dict[str, Any]]) -> str:
    return ' ' + re.sub(r'[^a-z0-9 ]+', ' ', ' '.join(w['t'] for w in words).lower()) + ' '


def audit_layers(a: Audit, cid: str, clip: dict[str, Any], assets: dict[str, dict[str, Any]]) -> float:
    r = a.rules
    dur = float(clip['duration'])
    layers = clip.get('layers') or []
    cutaway_time = 0.0
    exclusive: list[tuple[float, float, str]] = []
    for layer in layers:
        lid, kind = layer.get('id', '?'), layer.get('type')
        s, e = float(layer.get('s', -1)), float(layer.get('e', -1))
        if kind not in LAYER_TYPES:
            a.fail(cid, 'layers.type', f'{lid}: unknown layer type {kind!r}')
            continue
        if not (0 - EPS <= s < e <= dur + 1e-3):
            a.fail(cid, 'layers.bounds', f'{lid}: {s}..{e} is outside the clip (0..{dur}); nothing may cross a clip boundary')
        if kind == 'background-replace' and r['background'] == 'preserve':
            a.fail(cid, 'background.preserve', f'{lid}: the background must not be replaced (edit_rules.background = preserve)')
        if kind == 'depth' and not layer.get('matte'):
            a.fail(cid, 'depth.matte', f'{lid}: a depth layer needs a person matte; without one, put the graphic in front instead')
        if kind in FULL_FRAME:
            cutaway_time += e - s
            if e - s > r['cutaway_max_seconds'] + 1e-6:
                a.fail(cid, 'cutaway.length', f'{lid}: {e - s:.2f}s away from the speaker (max {r["cutaway_max_seconds"]}s)')
        if kind in FULL_FRAME or kind == 'card':
            exclusive.append((s, e, lid))
        asset = assets.get(layer.get('asset', '')) if layer.get('asset') else None
        if layer.get('asset') and asset is None:
            a.fail(cid, 'assets.ledger', f'{lid}: asset {layer["asset"]!r} is not in the asset ledger')
        person = (asset or {}).get('person') or layer.get('person')
        if kind in {'photo', 'broll', 'overlay'} and person and r['people_require_spoken_name']:
            parts = [p for p in re.sub(r'[^a-z0-9 ]+', ' ', person.lower()).split() if len(p) >= 3]
            text = spoken(clip.get('words') or [])
            if not parts or not any(f' {p} ' in text for p in parts):
                a.fail(cid, 'people.named', f'{lid}: a photo of {person} appears but the name is never spoken in this clip')
    exclusive.sort()
    for (s0, e0, l0), (s1, e1, l1) in zip(exclusive, exclusive[1:]):
        if s1 < e0 - 1e-3:
            a.fail(cid, 'layers.overlap', f'{l0} and {l1} overlap: the speaker carries at most one card or cutaway at a time')
    return cutaway_time


def audit_clearance(a: Audit, cid: str, clip: dict[str, Any], canvas: dict[str, Any]) -> None:
    face = clip.get('face') or []
    keys = sorted((clip.get('camera') or {}).get('keys') or [], key=lambda k: k['t'])
    if not face or not keys:
        return
    H = canvas['height']
    oy = ((clip.get('camera') or {}).get('origin') or [0.5, 0.36])[1]

    def moved(t: float, y: float) -> float:
        c = camera_at(keys, t)
        return (oy + (y - oy) * c['s'] + c['y']) * H

    words = clip.get('words') or []
    covered = [(float(l['s']), float(l['e'])) for l in clip.get('layers') or [] if l.get('type') in FULL_FRAME]
    for ci, ch in enumerate(clip.get('chunks') or []):
        if 'y' not in ch or not ch.get('words'):
            continue
        s, e = words[ch['words'][0]]['s'], words[ch['words'][-1]]['e']
        if any(cs - EPS <= s and e <= ce + EPS for cs, ce in covered):
            continue
        rows = [f for f in face if s - 1e-6 <= f['t'] <= e + 1e-6 and 'mouth' in f]
        if not rows:
            continue
        size = float(ch.get('size_px', 86 if ch.get('big') else 68))
        top = ch['y'] * H - size * 0.57
        mouth = max(moved(f['t'], f['mouth']) for f in rows)
        if top - mouth < a.rules['caption_mouth_gap_px']:
            a.fail(cid, 'captions.mouth', f'chunk {ci} sits {top - mouth:.0f}px from the mouth (min {a.rules["caption_mouth_gap_px"]}px)')
    for layer in clip.get('layers') or []:
        if layer.get('type') != 'card' or 'box' not in layer:
            continue
        rows = [f for f in face if float(layer['s']) <= f['t'] <= float(layer['e']) and 'eye' in f]
        if not rows:
            continue
        eye = min(moved(f['t'], f['eye']) for f in rows)
        if eye - layer['box'][3] < a.rules['card_eye_clearance_px']:
            a.fail(cid, 'cards.eyes', f'{layer.get("id")}: card ends {eye - layer["box"][3]:.0f}px above the eyes (min {a.rules["card_eye_clearance_px"]}px)')


def audit(edit: dict[str, Any], rules: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    a = Audit(rules)
    canvas = edit.get('canvas') or {'width': 1080, 'height': 1920, 'fps': 30}
    assets = {x['id']: x for x in edit.get('assets') or [] if 'id' in x}
    for aid, asset in assets.items():
        if not str(asset.get('source', '')).strip() or not str(asset.get('license', '')).strip():
            a.fail(None, 'assets.ledger', f'asset {aid!r} needs a source and a licence or usage basis')
    total = cut = 0.0
    keys = anchors = 0
    for clip in edit.get('clips') or []:
        cid = clip.get('id', '?')
        dur = float(clip.get('duration', 0))
        if dur <= 0:
            a.fail(cid, 'clip.duration', 'duration must be positive')
            continue
        total += dur
        keys += audit_camera(a, cid, clip, canvas)
        audit_captions(a, cid, clip)
        cut += audit_layers(a, cid, clip, assets)
        audit_clearance(a, cid, clip, canvas)
        for cue in clip.get('cues') or []:
            if not 0 <= float(cue.get('at', -1)) < dur:
                a.fail(cid, 'cues.bounds', f'cue {cue.get("asset")} at {cue.get("at")} is outside the clip')
            if cue.get('asset') not in assets:
                a.fail(cid, 'assets.ledger', f'cue sound {cue.get("asset")!r} is not in the asset ledger')
            anchors += cue.get('role') == 'anchor'
    if not edit.get('clips'):
        a.fail(None, 'clip.none', 'edit.json has no clips')
    share = cut / total if total else 0.0
    if share > rules['cutaway_share_max'] + 1e-6:
        a.fail(None, 'cutaway.share', f'cutaways cover {100 * share:.1f}% of the video (max {100 * rules["cutaway_share_max"]:.0f}%): the speaker is the main character')
    if anchors > rules['max_anchor_hits']:
        a.fail(None, 'cues.anchor', f'{anchors} anchor hits (max {rules["max_anchor_hits"]}): keep one biggest hit for the one biggest moment')
    metrics = {'duration': round(total, 3), 'cutaway_seconds': round(cut, 3), 'cutaway_share': round(share, 4),
               'speaker_share': round(1 - share, 4), 'camera_keys': keys, 'anchor_hits': anchors,
               'clips': len(edit.get('clips') or [])}
    return a.findings, metrics


def resolve_rules(edit: dict[str, Any], config_path: str | None) -> dict[str, Any]:
    rules = dict(DEFAULT_RULES)
    if config_path and Path(config_path).exists():
        rules.update(read_json(Path(config_path)).get('edit_rules') or {})
    rules.update(edit.get('rules') or {})
    return rules


def main() -> None:
    parser = argparse.ArgumentParser(description='m-edit editing rules as code')
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('camera', help='generate sine-eased camera keys for one clip')
    c.add_argument('--duration', type=float, required=True)
    c.add_argument('--punch', type=float, nargs='*', default=[])
    c.add_argument('--jump', type=float, nargs='*', default=[])
    c.add_argument('--seed', type=int, default=0)
    c.add_argument('--origin', type=float, nargs=2, default=[0.5, 0.36])
    c.add_argument('--width', type=int, default=1080)
    c.add_argument('--height', type=int, default=1920)
    c.add_argument('--shake-px', type=float, default=0.0)
    c.add_argument('--config')
    c = sub.add_parser('audit', help='audit edit.json against the editing rules')
    c.add_argument('--edit', required=True)
    c.add_argument('--output', required=True)
    c.add_argument('--config')
    args = parser.parse_args()
    if args.command == 'camera':
        rules = resolve_rules({}, args.config)
        keys = generate_camera(args.duration, rules=rules, punches=args.punch, jumps=args.jump, seed=args.seed,
                               origin=tuple(args.origin), width=args.width, height=args.height, shake_px=args.shake_px)
        print(json.dumps(keys, indent=1))
        return
    edit_path = Path(args.edit).expanduser().resolve(strict=True)
    edit = read_json(edit_path)
    rules = resolve_rules(edit, args.config)
    findings, metrics = audit(edit, rules)
    report = {'passed': not findings, 'edit_path': str(edit_path), 'edit_sha256': sha256(edit_path),
              'rules': rules, 'metrics': metrics, 'findings': findings}
    write_json(Path(args.output).expanduser().resolve(), report)
    for f in findings:
        print(f'FAIL [{f["rule"]}] {f["clip"] or "reel"}: {f["message"]}')
    print(json.dumps(metrics))
    if findings:
        raise SystemExit(f'Edit audit failed with {len(findings)} finding(s)')
    print('EDIT AUDIT PASSED')


if __name__ == '__main__':
    main()
