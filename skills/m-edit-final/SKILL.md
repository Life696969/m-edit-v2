---
name: m-edit-final
description: Use when the user has explicitly approved the whole-video preview and each clip's high-quality final file must be rendered and verified without creative drift.
license: MIT
compatibility: Requires Remotion and FFmpeg/FFprobe.
metadata:
  version: "2.0.0"
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

2. Render from the source master at the delivery resolution and fps.
   * Only delivery settings differ from the preview.
   * Never change timing, captions, layers, camera, assets or the audio mix.
   * Never transcode a preview into a final.
3. Verify it against that clip's approved preview. The comparison resamples fps and scales to the preview.

```bash
m-edit verify --input "<final>" --output "<verification>" --compare-preview "<approved preview>" --min-ssim "<render.fidelity_min_ssim>" --require-audio --contact-sheet "<sheet>"
```

4. Record it:

```bash
m-edit mark-reel-final --project "<folder>" --clip "<clip>" --path "<final>" --verification "<verification>"
```

* **On failure:** retry a failed clip once at concurrency 1. Delete temporary render folders after every attempt.
* **Every final is self-contained:** nothing crosses a clip boundary, the audio is trimmed to the exact picture duration, and played in order the clips are the video.

## STOP

Stop when every clip is verified (`all_clips_complete`). Report each final's path, duration, size, loudness and true peak, plus any retries. Merge only if the user asks for one file.
