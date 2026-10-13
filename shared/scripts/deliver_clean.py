#!/usr/bin/env python3
"""Clean final delivery: no metadata or encoder traces, top-notch single-encode audio, and two check rounds.

    m-edit deliver-clean deliver --project DIR --clip ID --render RENDER.mp4 --public DIR --output FINAL.mp4
                                 [--edit FILE] [--loudness voice-safe|standard]
    m-edit deliver-clean check FINAL.mp4 --project DIR --clip ID --render RENDER.mp4 --public DIR [--json-out FILE]
    m-edit deliver-clean clean --input COMPOSED.mp4 --output FINAL.mp4 [--audio LOSSLESS_MIX.wav]

`deliver` builds one clip's final from its rendered video and the audited `.m-edit/edit.json`, runs round 1 inline and
round 2 in a fresh process that re-derives and re-measures everything from disk, and only then writes `--output`. It
records `.m-edit/deliveries/<clip>/delivery_check.json` (and `.md`), which `mark-reel-final` requires.

Video: the rendered H.264 stream is copied bit for bit; only SEI NAL units (the encoder's settings banner) are dropped.

Audio: the approved mix is rebuilt losslessly from the same edit data the preview was rendered from: the clip's own
recording (gain only: no declipper, compressor or EQ), the music bed and the effect cues at their approved volumes and
times. One reel-wide gain keeps every balance exactly as approved. The loudness mode sets only its ceiling:

* `voice-safe`: as loud as the voice can be while no limiter ever touches it (the loudest take's loudest syllable stays
  under the ceiling), capped at -10.5 LUFS for the loudest take;
* `standard`: the reel's voice averages about -14 LUFS (never louder than voice-safe allows).

Where an effect or music transient coincides with a loud syllable, only the music/effects yield, just enough. A
4x-oversampled safety limiter (look-ahead compensated) may take at most 1 dB. The result is encoded once as AAC-LC at
320 kbps; if the encoder averages under the 300 kbps floor, that encode is discarded and redone from the same lossless
mix at a higher target, so a final always carries exactly one lossy generation. (Simple or dual-mono content can still
average under 300 kbps at any target; that is reported as a warning, because fidelity is checked directly.)

Container: no tags beyond brand, language and neutral handler names; `ftyp mp42`; no udta/meta/free/skip/uuid/btrt
boxes; `colr nclx` from the stream's VUI; short `esds`; real creation times (see mp4_scrub.py). Nothing is forged.

Needs FFmpeg/FFprobe (with the filter_units bitstream filter, alimiter and the native aac encoder) and numpy.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mp4_scrub  # noqa: E402
from common import read_json, sha256, write_json, now  # noqa: E402

try:
    import numpy as np
except ImportError:                                  # reported by `m-edit doctor`; only this command needs it
    np = None

SR = 48000
LIMIT = 0.85                     # -1.4 dBFS ceiling at 4x oversampling -> true peak about -1.4 dBTP
VOICE_MARGIN_DB = 0.3            # the loudest syllable stays this far under the ceiling: no limiter acts on the voice
LOUDNESS_MODES = {'voice-safe': -10.5, 'standard': -14.0}   # voice-safe: loudest take's cap; standard: reel average
STEM_LIMIT = 0.5                 # music + effects stem ceiling (-6 dBFS): shaves only transient attacks
YIELD_OVER_DB = 1.0              # the stem yields only beyond ceiling + 1 dB; the final limiter takes the last <= 1 dB
ATTACK_MS = 5
LOOKAHEAD = int(SR * ATTACK_MS / 1000)          # alimiter delays its output by its attack: pulled back
AAC = ['-c:a', 'aac', '-b:a', '320k', '-aac_coder', 'twoloop', '-ar', str(SR), '-ac', '2']
AAC_RETRY_TARGETS = ['352k', '384k']            # FFmpeg's AAC is average-bitrate: quiet content can undershoot 320k
MUX_COMMON = ['-map_metadata', '-1', '-map_metadata:s', '-1', '-map_chapters', '-1',
              '-fflags', '+bitexact', '-flags:v', '+bitexact', '-flags:a', '+bitexact',
              '-metadata:s:v', 'handler_name=Video', '-metadata:s:a', 'handler_name=Audio', '-movflags', '+faststart']

# ---- check thresholds (both rounds)
MAX_TRUE_PEAK = -1.0             # dBTP
MIN_AAC_KBPS = 300               # the average the encoder should reach; under it the encode is redone higher, then warned
MIN_SNR_DB = 18.0                # decoded final vs the intended pre-encode mix (AAC-LC 320k measures well above this)
MAX_LIMITER_GR_DB = 1.0
MAX_LAG = 1                      # samples
LUFS_RANGE = (-24.0, -9.0)       # sanity bounds: not silent, not crushed
ALLOWED_FORMAT_TAGS = {'major_brand', 'minor_version', 'compatible_brands', 'creation_time'}
ALLOWED_STREAM_TAGS = {'language', 'handler_name', 'creation_time', 'vendor_id'}
TRACE_PATTERNS = [rb'Lavf\d+\.\d+', rb'Lavc\d+\.\d+', rb'x264 - core', rb'libx264', rb'Remotion', rb'FFmpeg', rb'ffmpeg',
                  rb'Made with', rb'HandBrake', rb'CapCut', rb'c2pa', rb'jumbf', rb'xmpmeta',
                  rb'VideoHandler', rb'SoundHandler', rb'mdirappl']
FORBIDDEN_BOXES = {b'udta', b'meta', b'free', b'skip', b'uuid', b'btrt'}
NCLX = {'primaries': {'bt709': 1, 'unknown': 2, 'bt470m': 4, 'bt470bg': 5, 'smpte170m': 6, 'smpte240m': 7, 'bt2020': 9},
        'transfer': {'bt709': 1, 'unknown': 2, 'smpte170m': 6, 'iec61966-2-1': 13, 'smpte2084': 16, 'arib-std-b67': 18},
        'space': {'bt709': 1, 'unknown': 2, 'fcc': 4, 'bt470bg': 5, 'smpte170m': 6, 'bt2020nc': 9}}


def need_numpy() -> None:
    if np is None:
        raise SystemExit('deliver-clean needs numpy: run `python -m pip install numpy` (see `m-edit doctor`)')


# ======================================================================= helpers
def run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True, **kw)


def probe(path, entries: str, stream: str | None = None) -> dict[str, Any]:
    args = ['ffprobe', '-v', 'error'] + (['-select_streams', stream] if stream else []) + ['-show_entries', entries, '-of', 'json', str(path)]
    return json.loads(run(args, text=True).stdout)


def frames_fps(path) -> tuple[int, float]:
    out = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries',
               'stream=nb_read_frames,avg_frame_rate', '-of', 'csv=p=0', str(path)], text=True).stdout.strip().rstrip(',')
    rate, count = out.split(',')
    a, b = (int(x) for x in rate.split('/'))
    return int(count), a / b


def mix_samples(path) -> int:
    """Samples of audio to build for this video: its real duration (not frames / average fps, which is short on
    variable-rate footage) plus one AAC frame, so `-shortest` always ends on the video's last frame and never drops one."""
    streams = probe(path, 'stream=duration', 'v:0').get('streams') or [{}]
    seconds = float(streams[0].get('duration') or 0)
    if seconds <= 0:
        count, fps = frames_fps(path)
        seconds = count / fps
    return int(seconds * SR + 0.999999) + 1024


def has_audio(path) -> bool:
    return bool(probe(path, 'stream=codec_type', 'a').get('streams'))


def load_pcm(path, n: int | None = None):
    """Decode to float32 stereo 48 kHz; with n, trimmed or zero-padded to n samples (silence if there is no audio)."""
    if not has_audio(path):
        return np.zeros((n or 0, 2), np.float32)
    raw = run(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-']).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    if n is None:
        return x
    return np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]


def loudness(x) -> tuple[float, float]:
    p = subprocess.run(['ffmpeg', '-v', 'info', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                        '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                       input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    s = p.stderr.decode('utf-8', 'replace')
    j = json.loads(s[s.rindex('{'):s.rindex('}') + 1])
    return float(j['input_i']), float(j['input_tp'])


def db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-9)))


def video_md5(path) -> list[str]:
    out = run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:v:0', '-f', 'framemd5', '-'], text=True).stdout
    return [line.split(',')[-1].strip() for line in out.splitlines() if line and not line.startswith('#')]


def vui_codes(path) -> tuple[int, int, int, int]:
    j = probe(path, 'stream=color_primaries,color_transfer,color_space,color_range', 'v:0')['streams'][0]
    return (NCLX['primaries'].get(j.get('color_primaries', 'unknown'), 2), NCLX['transfer'].get(j.get('color_transfer', 'unknown'), 2),
            NCLX['space'].get(j.get('color_space', 'unknown'), 2), 1 if j.get('color_range') == 'pc' else 0)


def xcorr_lag(a, b, max_lag: int = 4000, seconds: int = 6) -> int:
    n = min(len(a), len(b), SR * seconds)
    a, b = a[:n] - a[:n].mean(), b[:n] - b[:n].mean()
    size = 1 << (2 * n - 1).bit_length()
    c = np.fft.irfft(np.fft.rfft(b, size) * np.conj(np.fft.rfft(a, size)), size)
    return int(np.argmax(np.concatenate([c[-max_lag:], c[:max_lag + 1]]))) - max_lag


def _window(x, w: int, how: str):
    """Centred sliding max/min over w samples (w odd), edge-padded: numpy only, in bounded-memory blocks."""
    half = w // 2
    padded = np.pad(x, half, mode='edge')
    out = np.empty_like(x)
    step = 1 << 18
    for i in range(0, len(x), step):
        view = np.lib.stride_tricks.sliding_window_view(padded[i:i + min(step, len(x) - i) + 2 * half], w)
        out[i:i + len(view)] = view.max(axis=1) if how == 'max' else view.min(axis=1)
    return out


def _mean(x, w: int):
    c = np.cumsum(np.pad(x, (w // 2 + 1, w // 2), mode='edge'))
    return (c[w:] - c[:-w]) / w


# ======================================================================= the mix
def limit(mix, tmp: Path, ceiling: float = LIMIT):
    """4x-oversampled peak limiter with its look-ahead removed (sync stays at 0 samples). Returns (audio, gain reduction dB)."""
    raw, out = tmp / 'mix.f32', tmp / 'mix_lim.f32'
    mix.astype(np.float32).tofile(raw)
    n = len(mix)
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', str(raw),
         '-af', f'aresample=192000,alimiter=level_in=1:level_out=1:limit={ceiling}:attack={ATTACK_MS}:release=50:level=false,'
                f'aresample={SR},atrim=start_sample={LOOKAHEAD},asetpts=N/SR/TB,apad,atrim=end_sample={n}',
         '-f', 'f32le', str(out)])
    y = np.fromfile(out, np.float32).reshape(-1, 2)[:n]
    gr = max(0.0, db(float(np.abs(mix).max())) - db(float(np.abs(y).max())))
    return y, round(gr, 2)


def voice_priority(voice, stem, ceiling: float = LIMIT * 0.97 * 10 ** (YIELD_OVER_DB / 20)):
    """Where a music/effect peak coinciding with a loud syllable would push the sum over the ceiling, ONLY the stem is
    turned down, just enough (held through the transient, 60 ms release). The voice is never touched."""
    w = int(0.004 * SR) | 1
    v = _window(np.abs(voice).max(1), w, 'max')
    s = _window(np.abs(stem).max(1), w, 'max')
    allowed = np.clip(ceiling - v, 0.02 * ceiling, None)
    g = np.minimum(1.0, allowed / np.maximum(s, 1e-9))
    if g.min() >= 1.0:
        return stem, 0.0
    g = _window(g, int(0.012 * SR) | 1, 'min')
    release = float(np.exp(-1.0 / (0.060 * SR)))
    out = np.empty_like(g)
    acc = 1.0
    for i, gi in enumerate(g.tolist()):                            # instant attack (already held early), smooth release
        acc = gi if gi < acc else acc * release + gi * (1 - release)
        out[i] = acc
    out = np.minimum(out, _mean(g, int(0.002 * SR) | 1) + 1.0)
    return stem * out[:, None], round(-db(float(out.min())), 2)


def dip_share(before, after) -> float:
    a, b = np.abs(before).max(1), np.abs(after).max(1)
    m = a > 1e-4
    return round(float(((b[m] / a[m]) < 0.891).mean() * 100) if m.any() else 0.0, 2)


class Reel:
    """The audited edit (`edit.json`), its Remotion public dir, and the reel-wide delivery gain."""

    def __init__(self, edit_path: Path, public: Path, mode: str):
        import edit_props                                          # same props the final was rendered from
        self.edit = read_json(edit_path)
        self.public = public
        self.mode = mode
        self._props = edit_props.build
        self._gain: dict[str, Any] | None = None

    def props(self, clip: str) -> dict[str, Any]:
        return self._props(self.edit, clip, 'final')

    def source(self, rel: str) -> Path:
        path = (self.public / rel).resolve()
        if not path.exists():
            raise SystemExit(f'missing under the public dir: {rel}')
        return path

    def voice(self, clip: str, n: int):
        """The clip's own recording, exactly as the preview played it (from 0, at full level), and nothing else."""
        return load_pcm(self.source(self.props(clip)['src']), n)

    def gain(self) -> dict[str, Any]:
        """One gain for the whole reel, so every balance (voice to music, take to take) stays as approved."""
        if self._gain is None:
            rows = []
            for clip in self.edit.get('clips') or []:
                n = int(round(float(clip['duration']) * SR))
                v = self.voice(clip['id'], n)
                peak = db(float(np.abs(v).max())) if len(v) else -120.0
                lufs = loudness(v)[0] if np.abs(v).max() > 1e-5 else -70.0
                rows.append({'clip': clip['id'], 'lufs': round(lufs, 2), 'peak_dbfs': round(peak, 2)})
            spoken = [r for r in rows if r['lufs'] > -60] or rows
            peak_gain = db(LIMIT) - VOICE_MARGIN_DB - max(r['peak_dbfs'] for r in rows)
            if self.mode == 'voice-safe':
                loud_gain = LOUDNESS_MODES['voice-safe'] - max(r['lufs'] for r in spoken)
            else:
                mean = 10 * np.log10(np.mean([10 ** (r['lufs'] / 10) for r in spoken]))
                loud_gain = LOUDNESS_MODES['standard'] - float(mean)
            g_db = min(loud_gain, peak_gain)
            self._gain = {'mode': self.mode, 'gain_db': round(g_db, 2), 'limited_by': 'voice peak' if peak_gain < loud_gain else 'loudness',
                          'takes': rows}
        return self._gain

    def intended_mix(self, clip: str, n: int, tmp: Path):
        """Pre-limiter float mix: voice (gain only) + the approved bed + cues, all at the one reel gain."""
        props = self.props(clip)
        g = 10 ** (self.gain()['gain_db'] / 20)
        voice = self.voice(clip, n) * g
        stem = np.zeros_like(voice)
        fps = float(props['fps'])
        bed = props.get('bed')
        if bed and float(bed.get('volume', 0)) > 0:
            track = load_pcm(self.source(bed['src']))
            b0 = int(round(round(float(bed['from']) * fps) / fps * SR))
            seg = track[b0:b0 + n]
            stem[:len(seg)] += seg * float(bed['volume']) * g
        for cue in props.get('cues') or []:
            s = int(round(max(0, round(float(cue['at']) * fps)) / fps * SR))
            sound = load_pcm(self.source(cue['src']))
            e = min(n, s + len(sound))
            if e > s:
                stem[s:e] += sound[:e - s] * float(cue.get('volume', 1.0)) * g
        stem_gr = 0.0
        if np.abs(stem).max() > STEM_LIMIT:
            stem, stem_gr = limit(stem, tmp, STEM_LIMIT)
        yielded, yield_db = voice_priority(voice, stem)
        info = {'voice_processing': 'gain only', 'loudness_mode': self.mode, 'reel_gain_db': self.gain()['gain_db'],
                'voice_peak_dbfs': round(db(float(np.abs(voice).max())), 2) if len(voice) else -120.0,
                'stem_transient_gr_db': stem_gr, 'stem_yield_max_db': yield_db, 'stem_dipped_time_pct': dip_share(stem, yielded)}
        return voice + yielded, info


# ======================================================================= build
def mux_aac(video_src, wav: Path, muxed: Path) -> str:
    """ONE AAC-LC encode of the lossless wav, muxed with the bit-exact video. An encode that averages under the bitrate
    floor is discarded and redone from the same wav at the next target. Returns the target kept."""
    target = '320k'
    for target in ['320k', *AAC_RETRY_TARGETS]:
        aac = [target if v == '320k' else v for v in AAC]
        run(['ffmpeg', '-y', '-v', 'error', '-i', str(video_src), '-i', str(wav), '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy',
             '-bsf:v', 'filter_units=remove_types=6', *aac, *MUX_COMMON, '-shortest', str(muxed)])
        kbps = int((probe(muxed, 'stream=bit_rate', 'a:0')['streams'] or [{}])[0].get('bit_rate', 0)) // 1000
        if kbps >= MIN_AAC_KBPS:
            break
    return target


def write_wav(x, path: Path) -> None:
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_f32le', str(path)],
        input=x.astype(np.float32).tobytes())


def build(reel: Reel, clip: str, render: Path, out: Path, tmp: Path) -> dict[str, Any]:
    n = mix_samples(render)
    mix, info = reel.intended_mix(clip, n, tmp)
    final_mix, gr = limit(mix, tmp)
    info['limiter_gr_db'] = gr
    wav = tmp / 'final_mix.wav'
    write_wav(final_mix, wav)
    muxed = tmp / 'muxed.mp4'
    info['aac_target'] = mux_aac(render, wav, muxed)
    mp4_scrub.scrub(muxed, out, *vui_codes(muxed))
    return info


# ======================================================================= checks
def check_metadata(path) -> tuple[list[str], dict[str, Any]]:
    fails: list[str] = []
    j = probe(path, 'format_tags:stream_tags:stream=codec_type')
    extra = set((j.get('format', {}).get('tags') or {}).keys()) - ALLOWED_FORMAT_TAGS
    if extra:
        fails.append(f'container tags present: {sorted(extra)}')
    for stream in j.get('streams', []):
        tags = stream.get('tags') or {}
        extra = set(tags) - ALLOWED_STREAM_TAGS
        if extra:
            fails.append(f"{stream.get('codec_type')} stream tags present: {sorted(extra)}")
        if tags.get('handler_name') not in (None, 'Video', 'Audio'):
            fails.append(f"handler name {tags.get('handler_name')!r}")
        if tags.get('creation_time', '2999').startswith(('1904', '1970', '0000')):
            fails.append('zeroed creation time')
    boxes = mp4_scrub.describe(path)
    bad = sorted(t.decode('latin1') for t in {t for _, t, _ in boxes} & FORBIDDEN_BOXES)
    if bad:
        fails.append(f'forbidden boxes: {bad}')
    for _, typ, payload in boxes:
        if typ == b'ftyp' and payload[:4] != b'mp42':
            fails.append(f'ftyp brand {payload[:4]!r} (FFmpeg default is isom)')
        if typ == b'colr' and payload[:4] != b'nclx':
            fails.append(f'colr {payload[:4]!r} (embedded ICC profile)')
        if typ == b'esds' and not mp4_scrub.esds_is_short(payload):
            fails.append("esds with FFmpeg's long descriptor sizes")
        if typ in (b'mvhd', b'tkhd', b'mdhd') and payload[4:8] == b'\x00\x00\x00\x00':
            fails.append(f'{typ.decode()} creation time is zero')
    with open(path, 'rb') as handle:
        blob = handle.read()
    found = sorted({m.group(0).decode('latin1') for pat in TRACE_PATTERNS for m in re.finditer(pat, blob)})
    if found:
        fails.append(f'trace strings: {found}')
    frames = run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-read_intervals', '%+#5', '-show_frames', '-of', 'json', str(path)],
                 text=True).stdout
    if 'User Data Unregistered' in frames:
        fails.append('SEI user data (encoder banner) in the video stream')
    if 'ICC profile' in frames:
        fails.append('embedded ICC profile')
    return fails, {'boxes': len(boxes)}


def check_audio_format(path):
    fails: list[str] = []
    streams = probe(path, 'stream=codec_name,profile,sample_rate,channels,bit_rate', 'a:0')['streams']
    if not streams:
        return ['no audio stream'], {}, None
    a = streams[0]
    info = {k: a.get(k) for k in ('codec_name', 'profile', 'sample_rate', 'channels', 'bit_rate')}
    if a.get('codec_name') != 'aac' or a.get('profile') != 'LC':
        fails.append(f"audio codec {a.get('codec_name')}/{a.get('profile')} (want AAC-LC)")
    if int(a.get('sample_rate', 0)) != SR or int(a.get('channels', 0)) != 2:
        fails.append(f"audio {a.get('sample_rate')} Hz x{a.get('channels')} (want 48000 x2)")
    if int(a.get('bit_rate', 0)) < MIN_AAC_KBPS * 1000:
        # A warning, not a failure: FFmpeg's AAC is average-bitrate and codes identical channels as mid/side, so a
        # dual-mono voice-only mix averages ~240 kbps at ANY target. The encode itself is always >= 320k (see mux_aac),
        # and fidelity is proven by the SNR-vs-lossless-mix and true-peak checks.
        info['warnings'] = [f"audio averages {int(a.get('bit_rate', 0)) // 1000} kbps (encoded at a >= 320k target; "
                            'simple or dual-mono content needs fewer bits)']
    dec = load_pcm(path)
    li, tp = loudness(dec)
    info.update({'lufs': round(li, 2), 'true_peak_dbtp': round(tp, 2), 'sample_peak_dbfs': round(db(float(np.abs(dec).max())), 2)})
    if tp > MAX_TRUE_PEAK:
        fails.append(f'true peak {tp:+.2f} dBTP (> {MAX_TRUE_PEAK})')
    if np.abs(dec).max() >= 0.999:
        fails.append('decoded samples reach full scale (clipping)')
    if not LUFS_RANGE[0] <= li <= LUFS_RANGE[1]:
        fails.append(f'loudness {li:.1f} LUFS outside {LUFS_RANGE}')
    return fails, info, dec


def check_video(path, reference=None) -> tuple[list[str], dict[str, Any]]:
    fails: list[str] = []
    errors = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'], capture_output=True, text=True).stderr.strip()
    if errors:
        fails.append(f'decode errors: {errors[:200]}')
    count, fps = frames_fps(path)
    info: dict[str, Any] = {'frames': count, 'fps': round(fps, 3)}
    if reference:
        ref_count, _ = frames_fps(reference)
        if ref_count != count:
            fails.append(f'{count} frames, the rendered video has {ref_count}')
        elif video_md5(path) != video_md5(reference):
            fails.append('video frames differ from the render (must be a bit-exact copy)')
        else:
            info['video'] = 'bit-exact copy of the render'
    return fails, info


def _compare(ref, dec, label: str) -> tuple[list[str], dict[str, Any]]:
    fails: list[str] = []
    lag = xcorr_lag(ref.mean(1), dec.mean(1))
    info: dict[str, Any] = {'lag_vs_intended': lag}
    if abs(lag) > MAX_LAG:
        fails.append(f'audio is {lag:+d} samples off {label}')
    k = min(len(ref), len(dec))
    r, d = ref[:k].mean(1), dec[:k].mean(1)
    snr = 10 * np.log10(max(float((r ** 2).sum()), 1e-20) / max(float(((d - r) ** 2).sum()), 1e-20))
    info['snr_vs_intended_db'] = round(float(snr), 1)
    if snr < MIN_SNR_DB:
        fails.append(f'delivered audio deviates from {label} (SNR {snr:.1f} dB < {MIN_SNR_DB})')
    return fails, info


def check_against_intent(reel: Reel, clip: str, dec, tmp: Path) -> tuple[list[str], dict[str, Any]]:
    """Re-derive the intended mix in this process; compare the delivered audio with it and with the recording."""
    n = len(dec)
    mix, info = reel.intended_mix(clip, n, tmp)
    ref, gr = limit(mix, tmp)
    info['limiter_gr_db'] = gr
    fails: list[str] = []
    if gr > MAX_LIMITER_GR_DB:
        fails.append(f'final limiter gain reduction {gr:.1f} dB (> {MAX_LIMITER_GR_DB})')
    if info['voice_peak_dbfs'] > db(LIMIT):
        fails.append(f"the voice alone peaks at {info['voice_peak_dbfs']:+.2f} dBFS, above the limiter ceiling")
    more, cmp = _compare(ref, dec, 'the intended mix')
    fails += more
    info.update(cmp)
    voice = reel.voice(clip, n)
    if np.abs(voice).max() > 1e-4:
        info['lag_vs_source'] = xcorr_lag(voice.mean(1), dec.mean(1))
        if abs(info['lag_vs_source']) > MAX_LAG:
            fails.append(f"audio is {info['lag_vs_source']:+d} samples off the original recording")
    return fails, info


def check_against_mix(mix_path: Path, dec, tmp: Path) -> tuple[list[str], dict[str, Any]]:
    """clean mode: the delivered audio vs the lossless mix it was encoded from (same safety limiter re-applied)."""
    x = load_pcm(mix_path, len(dec))
    ref, gr = limit(x, tmp)
    fails, info = _compare(ref, dec, 'the lossless mix')
    info['limiter_gr_db'] = gr
    if gr > MAX_LIMITER_GR_DB:
        fails.append(f'the mix is too hot: the safety limiter took {gr:.1f} dB (> {MAX_LIMITER_GR_DB}); lower it upstream')
    return fails, info


def check_file(path: Path, reel: Reel | None = None, clip: str | None = None, render: Path | None = None,
               audio_ref: Path | None = None) -> tuple[list[str], dict[str, Any]]:
    tmp = Path(tempfile.mkdtemp(prefix='m-edit-deliver-'))
    try:
        f1, i1 = check_metadata(path)
        f2, i2, dec = check_audio_format(path)
        f3, i3 = check_video(path, render)
        f4: list[str] = []
        i4: dict[str, Any] = {}
        if dec is not None and reel is not None and clip:
            f4, i4 = check_against_intent(reel, clip, dec, tmp)
        elif dec is not None and audio_ref is not None:
            f4, i4 = check_against_mix(audio_ref, dec, tmp)
        return f1 + f2 + f3 + f4, {**i1, **i2, **i3, **i4}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ======================================================================= reports
def clip_key(clip: str) -> str:
    return re.sub(r'[^A-Za-z0-9._-]', '_', clip)


def report_md(result: dict[str, Any]) -> str:
    lines = [f"# Delivery check: {result['name']}", '',
             'Round 1 runs inline while building; round 2 is a fresh process that re-derives and re-measures everything',
             'from the files on disk. A final is delivered only when both rounds pass.', '',
             '| Round | Result | LUFS | True peak | AAC | Voice | Limiter | SNR vs intended | Lag (intended / source) | Video |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for label in ('round1', 'round2'):
        r = result.get(label)
        if not r:
            continue
        i = r['info']
        lines.append(f"| {label[-1]} | {'PASS' if r['passed'] else 'FAIL'} | {i.get('lufs', '')} | {i.get('true_peak_dbtp', '')} dBTP | "
                     f"{int(i.get('bit_rate') or 0) // 1000} kbps {i.get('profile', '')} | {i.get('voice_processing', '')} "
                     f"({i.get('loudness_mode', '')}, reel gain {i.get('reel_gain_db', '')} dB, peak {i.get('voice_peak_dbfs', '')} dBFS) | "
                     f"{i.get('limiter_gr_db', '')} dB | {i.get('snr_vs_intended_db', '')} dB | "
                     f"{i.get('lag_vs_intended', '')} / {i.get('lag_vs_source', '')} | {i.get('frames', '')} frames, {i.get('video', '')} |")
        for fail in r['fails']:
            lines.append(f'|  | **{fail}** |  |  |  |  |  |  |  |  |')
        for warning in i.get('warnings') or []:
            lines.append(f'|  | warning: {warning} |  |  |  |  |  |  |  |  |')
    lines += ['', 'Metadata: no tags beyond brand, language and neutral handler names; no udta/meta/free/skip/uuid/btrt boxes; '
              'ftyp mp42; colr nclx (no ICC); short esds; real creation times; no Lavf/Lavc/x264/FFmpeg/Remotion/C2PA/XMP '
              'strings; no SEI user data. Nothing forged.']
    return '\n'.join(lines) + '\n'


def write_reports(result: dict[str, Any], folder: Path, stem: str = 'delivery_check') -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / f'{stem}.json', result)
    (folder / f'{stem}.md').write_text(report_md(result), encoding='utf-8')
    return folder / f'{stem}.json'


def config_mode(project: Path) -> str:
    try:
        config = read_json(project / '.m-edit' / 'config.json')
    except (OSError, ValueError, SystemExit):
        config = {}
    return (config.get('delivery') or {}).get('loudness', 'voice-safe')


# ======================================================================= commands
def round2(args_list: list[str]) -> tuple[bool, dict[str, Any]]:
    """Run the independent check in a fresh process; returns (passed, its JSON result)."""
    with tempfile.TemporaryDirectory(prefix='m-edit-round2-') as folder:
        out = Path(folder) / 'round2.json'
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), 'check', *args_list, '--json-out', str(out)],
                              capture_output=True, text=True)
        if not out.exists():
            raise SystemExit(f'round 2 did not run: {proc.stderr[-1500:]}')
        payload = read_json(out)
    return proc.returncode == 0 and payload.get('passed') is True, payload


def cmd_deliver(a) -> None:
    need_numpy()
    project = Path(a.project).expanduser().resolve(strict=True)
    edit = Path(a.edit).expanduser().resolve(strict=True) if a.edit else project / '.m-edit' / 'edit.json'
    public = Path(a.public).expanduser().resolve(strict=True)
    render = Path(a.render).expanduser().resolve(strict=True)
    output = Path(a.output).expanduser().resolve()
    mode = a.loudness or config_mode(project)
    if mode not in LOUDNESS_MODES:
        raise SystemExit(f'--loudness must be one of {sorted(LOUDNESS_MODES)}')
    folder = project / '.m-edit' / 'deliveries' / clip_key(a.clip)
    stage = folder / 'staging'
    stage.mkdir(parents=True, exist_ok=True)
    staged = stage / output.name
    tmp = Path(tempfile.mkdtemp(prefix='m-edit-deliver-'))
    result: dict[str, Any] = {'name': a.clip, 'clip': a.clip, 'loudness_mode': mode, 'render_sha256': sha256(render),
                              'edit_sha256': sha256(edit), 'created_at': now(), 'passed': False}
    try:
        reel = Reel(edit, public, mode)
        info = build(reel, a.clip, render, staged, tmp)
        fails, checked = check_file(staged, reel, a.clip, render)                                   # round 1
        result['reel_gain'] = reel.gain()
        result['round1'] = {'passed': not fails, 'fails': fails, 'info': {**checked, **info}}
        if fails:
            write_reports(result, folder)
            raise SystemExit('round 1 failed; nothing delivered:\n  - ' + '\n  - '.join(fails))
        ok, r2 = round2([str(staged), '--project', str(project), '--clip', a.clip, '--render', str(render),
                         '--public', str(public), '--edit', str(edit), '--loudness', mode])
        result['round2'] = r2.get('files', [{}])[0]
        if not ok:
            write_reports(result, folder)
            raise SystemExit('round 2 failed; nothing delivered:\n  - ' + '\n  - '.join(result['round2'].get('fails', [])))
        output.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, output)
        result.update({'passed': True, 'final_path': str(output), 'final_sha256': sha256(output)})
        report = write_reports(result, folder)
        shutil.rmtree(stage, ignore_errors=True)
        print(json.dumps({'passed': True, 'final': str(output), 'delivery': str(report),
                          'lufs': result['round2']['info'].get('lufs'), 'true_peak_dbtp': result['round2']['info'].get('true_peak_dbtp')}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_check(a) -> None:
    need_numpy()
    reel = None
    if a.project:
        project = Path(a.project).expanduser().resolve(strict=True)
        edit = Path(a.edit).expanduser().resolve(strict=True) if a.edit else project / '.m-edit' / 'edit.json'
        if not a.public or not a.clip:
            raise SystemExit('check with --project also needs --clip and --public')
        reel = Reel(edit, Path(a.public).expanduser().resolve(strict=True), a.loudness or config_mode(project))
    rows, bad = [], 0
    for name in a.files:
        path = Path(name).expanduser().resolve(strict=True)
        fails, info = check_file(path, reel, a.clip, Path(a.render).resolve() if a.render else None,
                                 Path(a.audio_ref).resolve() if a.audio_ref else None)
        rows.append({'file': str(path), 'passed': not fails, 'fails': fails, 'info': info})
        bad += bool(fails)
        print(f"[round 2] {path.name}: {'PASS' if not fails else 'FAIL'}  LUFS {info.get('lufs')} TP {info.get('true_peak_dbtp')} "
              f"SNR {info.get('snr_vs_intended_db')} lag {info.get('lag_vs_intended')}/{info.get('lag_vs_source')} "
              f"limiter {info.get('limiter_gr_db')} {info.get('frames')}f {info.get('video', '')}"
              + ('' if not fails else '\n    - ' + '\n    - '.join(fails)), flush=True)
    if a.json_out:
        write_json(Path(a.json_out), {'passed': not bad, 'files': rows})
    raise SystemExit(1 if bad else 0)


def cmd_clean(a) -> None:
    """For files m-edit did not render: video copied bit for bit (SEI dropped). Audio: with --audio, ONE AAC-LC encode
    of that lossless mix behind the <= 1 dB safety limiter; without it, the input's audio is copied only if it carries
    no encoder signature (re-encoding lossy audio would add a generation, so it is refused)."""
    need_numpy()
    source = Path(a.input).expanduser().resolve(strict=True)
    output = Path(a.output).expanduser().resolve()
    audio = Path(a.audio).expanduser().resolve(strict=True) if a.audio else None
    stage = output.parent / '.m-edit-delivery-staging'
    stage.mkdir(parents=True, exist_ok=True)
    staged = stage / output.name
    tmp = Path(tempfile.mkdtemp(prefix='m-edit-clean-'))
    result: dict[str, Any] = {'name': output.name, 'input_sha256': sha256(source), 'created_at': now(), 'passed': False}
    try:
        muxed = tmp / 'muxed.mp4'
        info: dict[str, Any] = {}
        if audio:
            mix, gr = limit(load_pcm(audio, mix_samples(source)), tmp)
            info['limiter_gr_db'] = gr
            write_wav(mix, tmp / 'mix.wav')
            info['aac_target'] = mux_aac(source, tmp / 'mix.wav', muxed)
        else:
            with open(source, 'rb') as handle:
                if re.search(rb'Lavc\d+\.\d+', handle.read()):
                    raise SystemExit("the input's audio carries an encoder signature; re-encoding lossy audio would add a "
                                     'generation. Pass --audio <the lossless mix it was built from>.')
            run(['ffmpeg', '-y', '-v', 'error', '-i', str(source), '-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy',
                 '-bsf:v', 'filter_units=remove_types=6', *MUX_COMMON, str(muxed)])
        mp4_scrub.scrub(muxed, staged, *vui_codes(muxed))
        fails, checked = check_file(staged, render=source, audio_ref=audio)                          # round 1
        result['round1'] = {'passed': not fails, 'fails': fails, 'info': {**checked, **info}}
        if fails:
            write_reports(result, output.parent, f'{output.stem}.delivery_check')
            raise SystemExit('round 1 failed; nothing delivered:\n  - ' + '\n  - '.join(fails))
        ok, r2 = round2([str(staged), '--render', str(source)] + (['--audio-ref', str(audio)] if audio else []))
        result['round2'] = r2.get('files', [{}])[0]
        if not ok:
            write_reports(result, output.parent, f'{output.stem}.delivery_check')
            raise SystemExit('round 2 failed; nothing delivered:\n  - ' + '\n  - '.join(result['round2'].get('fails', [])))
        os.replace(staged, output)
        result.update({'passed': True, 'final_path': str(output), 'final_sha256': sha256(output)})
        report = write_reports(result, output.parent, f'{output.stem}.delivery_check')
        print(json.dumps({'passed': True, 'final': str(output), 'delivery': str(report)}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(stage, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description='Clean final delivery: no metadata, top-notch audio, two check rounds.')
    sub = parser.add_subparsers(dest='command', required=True)
    d = sub.add_parser('deliver', help='build, check twice and write one clip final')
    d.add_argument('--project', required=True)
    d.add_argument('--clip', required=True, help='the clip id in edit.json')
    d.add_argument('--render', required=True, help="the clip's rendered final (Remotion output)")
    d.add_argument('--public', required=True, help='the Remotion public dir the props paths are relative to')
    d.add_argument('--output', required=True, help='where the clean final is written')
    d.add_argument('--edit', help='default: <project>/.m-edit/edit.json')
    d.add_argument('--loudness', choices=sorted(LOUDNESS_MODES), help='default: config delivery.loudness (voice-safe)')
    c = sub.add_parser('check', help='round-2 checks (also usable on any MP4)')
    c.add_argument('files', nargs='+')
    c.add_argument('--project')
    c.add_argument('--clip')
    c.add_argument('--render')
    c.add_argument('--public')
    c.add_argument('--edit')
    c.add_argument('--loudness', choices=sorted(LOUDNESS_MODES))
    c.add_argument('--audio-ref', help='clean mode: the lossless mix the audio was encoded from')
    c.add_argument('--json-out')
    k = sub.add_parser('clean', help='clean a final m-edit did not render')
    k.add_argument('--input', required=True)
    k.add_argument('--output', required=True)
    k.add_argument('--audio', help='the lossless mix (wav/flac) the input was built from')
    a = parser.parse_args()
    {'deliver': cmd_deliver, 'check': cmd_check, 'clean': cmd_clean}[a.command](a)


if __name__ == '__main__':
    main()
