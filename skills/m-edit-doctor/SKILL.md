---
name: m-edit-doctor
description: Use when m-edit installation, FFmpeg, Remotion, transcription, configuration, permissions, or project readiness is failing or uncertain.
license: MIT
compatibility: Requires Python 3.10+ for the bundled diagnostic command.
metadata:
  version: "2.0.0"
---

# Diagnose m-edit

**Resolve `<suite-root>` first:** use `${CLAUDE_PLUGIN_ROOT}` when it contains `shared/`; otherwise `${M_EDIT_HOME}/current`; otherwise the nearest `.m-edit-suite/current` above the video project; otherwise `~/.m-edit/current`. Confirm `VERSION` and `shared/scripts/cli.py` exist. If none is valid, stop with installation guidance.


Resolve `<suite-root>` and run:

```bash
<suite-root>/bin/m-edit doctor --project "<video-folder>"
<suite-root>/bin/m-edit validate-config --config "<video-folder>/.m-edit/config.json"
```

Explain every failed required check and warning. List what is missing in one message, with the install command for each item. Do not install packages, download models, or rewrite state without explicit user authorization. For state problems, run `m-edit-status` and preserve `.m-edit/` as evidence before recommending recovery.
