---
name: m-edit-merge
description: Use when every individual final is verified and the user explicitly asks to combine them into one ordered video.
license: MIT
compatibility: Requires FFmpeg/FFprobe or an equivalent deterministic merge path.
metadata:
  version: "2.0.0"
---

# Merge verified finals

**Resolve `<suite-root>` first:** use `${CLAUDE_PLUGIN_ROOT}` when it contains `shared/`; otherwise `${M_EDIT_HOME}/current`; otherwise the nearest `.m-edit-suite/current` above the video project; otherwise `~/.m-edit/current`. Confirm `VERSION` and `shared/scripts/cli.py` exist. If none is valid, stop with installation guidance.


Run:

```bash
<suite-root>/bin/m-edit guard --project "<video-folder>" --kind merge
```

Use only verified finals in the recorded order. Preserve synchronization. Use stream copy only when codecs, dimensions, FPS, time bases, and audio formats are compatible; otherwise perform one documented high-quality encode.

Verify the merged output independently, create a contact sheet, and write a merge report listing every input path and hash. Record completion:

```bash
<suite-root>/bin/m-edit verify --input "<merged>" --output "<verification>" --contact-sheet "<contact-sheet>" [--require-audio]
<suite-root>/bin/m-edit mark-merged --project "<video-folder>" --path "<merged-relative-path>" --verification "<verification-relative-path>"
```

A request for individual finals is not a merge request.

## STOP

Stop after the verified merged output and report are recorded. Do not alter individual finals or begin another project automatically.
