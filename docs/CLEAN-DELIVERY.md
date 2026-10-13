# Clean final delivery

**Since 2.1.0.** Every final m-edit records is **clean** unless the user explicitly opts out:

1. it carries **no metadata or encoder traces**, neither text tags nor structural fingerprints, and nothing is forged;
2. its audio is **faithful to the original recording**: the voice at gain only, at the loudness the user picked, encoded once;
3. it passes **two independent check rounds** before `mark-reel-final` accepts it.

## Why

A Remotion/FFmpeg render carries:

* a `comment` ("Made with Remotion …") and `encoder` tags (`Lavf…`, `Lavc… libx264`);
* the default handler names (`VideoHandler`/`SoundHandler`);
* the x264 settings banner as an H.264 SEI message;
* FFmpeg's AAC encoder signature inside the audio stream.

After the text tags are removed, the MP4 structure still identifies the toolchain:

* the `isom`/512/`isomiso2avc1mp41` `ftyp` brands;
* an empty iTunes `udta/meta` box;
* `free` and `btrt` boxes;
* an ICC profile from the headless browser;
* long-form `esds` descriptor sizes;
* zeroed creation times.

Creators may prefer finals without these traces. Some believe platforms treat tool traces as a signal; that belief is unverified, and the documented AI labels key on C2PA/IPTC markers.

Audio also degrades when the voice is declipped or compressed by default, or passes through several lossy generations.

## Where it runs

In `m-edit-final`, for each clip: render → **`m-edit deliver-clean deliver`** → `m-edit verify` (against the approved preview) → `m-edit mark-reel-final --delivery <report>`.

```bash
m-edit deliver-clean deliver --project <folder> --clip <clip id> --render <rendered.mp4> --public <remotion public dir> --output <final.mp4>
```

It writes `.m-edit/deliveries/<clip>/delivery_check.json` and `.md`. `mark-reel-final` refuses a final without a report that passed **both** rounds for exactly that file (matched by SHA-256), unless `delivery.clean` is `false`.

For a file m-edit did not render:

```bash
m-edit deliver-clean clean --input <composed.mp4> --audio <lossless mix.wav> --output <final.mp4>
```

Without `--audio`, the input's audio is copied only if it carries no encoder signature. Re-encoding already-lossy audio would add a generation, so it is refused.

## Configuration (`.m-edit/config.json`)

```json
"delivery": {"clean": true, "loudness": "voice-safe"}
```

| Key | Values | Set by |
|---|---|---|
| `clean` | `true` (default) / `false` | `false` only on the user's explicit request; the final report quotes it |
| `loudness` | `voice-safe` (default) / `standard` | the user's answer to question 3 of the direction interview |

Configs from 2.0 have no `delivery` section and get the defaults. The section is not bound into the approved context: it changes neither the approved picture nor the mix balance.

## What a final gets

**Video:** the rendered H.264 stream is copied **bit for bit**. Only SEI NAL units are dropped (`-bsf:v filter_units=remove_types=6`).

**Audio:** the approved mix is rebuilt **losslessly** from the audited `edit.json`, through the same `edit-props` the final was rendered from:

* the clip's own recording at **gain only**: no declipper, no compressor, no EQ;
* the music bed and the effect cues at their approved volumes and frame-rounded times;
* **one gain for the whole video**, so every balance (voice to music, take to take) stays exactly as approved. Its ceiling comes from the loudness mode:
  * `voice-safe`: as loud as the voice can be while no limiter ever touches it. The loudest take's loudest syllable stays 0.3 dB under the −1.4 dBFS ceiling, and the loudest take is capped at −10.5 LUFS;
  * `standard`: the takes average about −14 LUFS, never louder than voice-safe allows;
* music and effects **yield** to the voice only where a hit coincides with a loud syllable, and only enough to fit;
* a 4× oversampled **safety limiter** that may take at most 1 dB, with its look-ahead compensated (sync stays at 0 samples);
* **one** AAC-LC encode at 320k, 48 kHz stereo. If FFmpeg's average-bitrate encoder averages under 300 kbps, the encode is discarded and redone from the same lossless mix at 352k, then 384k. Simple or dual-mono content (a voice-only mono mic) can average about 240 kbps at any target, because identical channels code as mid/side; that is reported as a **warning**, not a failure, because fidelity is checked directly.

**Container** (`shared/scripts/mp4_scrub.py`):

* no tags beyond brand, language and neutral handler names (`Video`/`Audio`);
* `ftyp mp42`;
* no `udta`/`meta`/`free`/`skip`/`uuid`/`btrt` boxes;
* `colr nclx` from the stream's own colour description (no ICC);
* short-form `esds`;
* the real creation time, with chunk offsets patched for the removed bytes.

**Never forged:** camera, date and provenance metadata are only ever removed.

## The two rounds

**Round 1** runs inline after building. **Round 2** runs in a fresh process that re-derives the intended mix from `edit.json` and re-measures everything from disk. A final that fails either round is not written to `--output`; the staged file is kept under `.m-edit/deliveries/<clip>/staging/` for inspection.

| Area | Check |
|---|---|
| Metadata | no extra tags; no forbidden boxes; `ftyp` mp42; `colr` nclx; short `esds`; non-zero times; no `Lavf`/`Lavc`/`x264`/`FFmpeg`/`Remotion`/C2PA/XMP/handler strings; no SEI user data or ICC side data |
| Audio format | AAC-LC, 48 kHz, stereo; the average bitrate is reported (under 300 kbps is a warning) |
| Audio quality | true peak ≤ −1.0 dBTP; no full-scale samples; −24 to −9 LUFS (sanity bounds); the voice alone under the limiter ceiling; final limiter ≤ 1 dB; SNR of the decoded final vs the intended mix ≥ 18 dB; lag ≤ 1 sample vs the intended mix and the original recording |
| Video | 0 decode errors; frame count and per-frame MD5 identical to the render |

**When a round fails,** fix the cause, never the check. The usual cause is a mix too hot for the 1 dB limiter: lower the bed or a cue in `edit.json`, re-audit, re-render and deliver again.

## Requirements

FFmpeg/FFprobe with the `filter_units` bitstream filter, the `alimiter` filter and the native `aac` encoder, plus numpy. `m-edit doctor` checks all four (`clean-delivery`).

## Tests

`tests/test_delivery.py`:

* a dirty render fails the metadata checks, and the scrub makes it pass with identical decoded samples;
* a one-clip project delivers through both rounds with 0 lag, a voice-safe level, a gain-only voice, ≥ 18 dB SNR and a bit-exact video;
* `standard` is quieter than `voice-safe`, and neither ever lets the voice reach the ceiling;
* an undershooting AAC encode is redone from the lossless mix;
* a dual-mono mix is warned, not refused;
* lossy audio is never re-encoded;
* `mark-reel-final` accepts only a passing two-round report for exactly this final, unless the user opted out.

## Reference

Ported from the maintainer's own delivery tooling, which was validated on real multi-clip reels (both rounds passing, SNR 35–46 dB, lag 0, video bit-exact) and on a Short built by a separate FFmpeg pipeline.
