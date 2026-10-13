---
name: m-edit-final
description: Use when the user has explicitly approved the whole-video preview and each clip's high-quality final file must be rendered and verified without creative drift.
license: MIT
compatibility: Requires Remotion and FFmpeg/FFprobe.
metadata:
  version: "2.1.0"
---

# Render every final, each as its own file

**Resolve `<suite-root>` first:** `${CLAUDE_PLUGIN_ROOT}` when it contains `shared/`; otherwise `${M_EDIT_HOME}/current`; otherwise the nearest `.m-edit-suite/current`; otherwise `~/.m-edit/current`.

Allowed only in `finalizing_reel`, after the whole-video approval:

```bash
m-edit guard --project "<folder>" --kind final
```

## Before rendering

Check free memory and disk. Plan heavy clips (4K, an alpha matte) for `render.retry_concurrency`, with `render.renderer_timeout_ms`.

## For each clip, in order

1. Generate the final props from the **same** `.m-edit/edit.json`:

```bash
m-edit edit-props --edit .m-edit/edit.json --clip "<clip>" --preset final --output "<props>"
```

2. Render from the source master at the delivery resolution and fps, into a working path (for example `.m-edit/renders/<clip>.mp4`).
   * Only delivery settings differ from the preview.
   * Never change timing, captions, layers, camera, assets or the audio mix.
   * Never transcode a preview into a final.
3. **Deliver it clean** (on by default; see `<suite-root>/shared/references/sound-design.md` → Delivery):

```bash
m-edit deliver-clean deliver --project "<folder>" --clip "<clip>" --render "<render>" --public "<remotion public dir>" --output "<final>"
```

   * The video is copied bit for bit; only the encoder's settings banner (SEI) is dropped.
   * The audio is rebuilt losslessly from the audited `edit.json`: the clip's own recording at **gain only** (no declipper, compressor or EQ), the music bed and the cues at their approved volumes, one reel-wide gain at the loudness the user chose (`delivery.loudness`: `voice-safe` or `standard`), a safety limiter of at most 1 dB, and **one** AAC-LC encode at ≥ 320k.
   * Every metadata tag, encoder string and FFmpeg box fingerprint is removed. Nothing is forged.
   * Round 1 runs inline and round 2 in a fresh process. **A clip that fails either round gets no final:** fix the cause (for example, a mix too hot for the 1 dB limiter), never the check.
   * It writes `.m-edit/deliveries/<clip>/delivery_check.json` and `.md`.
   * Skip this step only if the user **explicitly** asked to keep the original file as rendered. Then set `delivery.clean` to `false` in `.m-edit/config.json` and quote their words in the final report.
4. Verify the delivered final against that clip's approved preview. The comparison resamples fps and scales to the preview.

```bash
m-edit verify --input "<final>" --output "<verification>" --compare-preview "<approved preview>" --min-ssim "<render.fidelity_min_ssim>" --require-audio --contact-sheet "<sheet>"
```

5. Record it with its delivery report:

```bash
m-edit mark-reel-final --project "<folder>" --clip "<clip>" --path "<final>" --verification "<verification>" --delivery ".m-edit/deliveries/<clip>/delivery_check.json"
```

* **On failure:** retry a failed render once at concurrency 1. Delete temporary render folders after every attempt, and delete the working render once its clean final is recorded.
* **Every final is self-contained:** nothing crosses a clip boundary, the audio is trimmed to the exact picture duration, and played in order the clips are the video.

## STOP

Stop when every clip is verified (`all_clips_complete`). Report each final's path, duration, size, loudness and true peak, the two delivery rounds (with any warning), plus any retries. Merge only if the user asks for one file.
