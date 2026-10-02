---
name: m-edit-status
description: Use when a user asks what an m-edit project completed, what is waiting for them, whether source clips changed, why something is blocked, or how to resume.
license: MIT
compatibility: Requires read access to the project's `.m-edit` directory.
metadata:
  version: "2.0.0"
---

# Report state without changing it

**Resolve `<suite-root>` first:** use `${CLAUDE_PLUGIN_ROOT}` when it contains `shared/`; otherwise `${M_EDIT_HOME}/current`; otherwise the nearest `.m-edit-suite/current` above the video project; otherwise `~/.m-edit/current`. Confirm `VERSION` and `shared/scripts/cli.py` exist. If none is valid, stop with installation guidance.


Run:

```bash
<suite-root>/bin/m-edit status --project "<video-folder>"
```

Report:

* the current phase
* whether the questions are answered
* each clip's preview version and status
* whether the whole-video review is pending or approved
* recipe and code integrity
* final verification
* merge eligibility
* warnings
* one exact next action

Do not create media or mutate state.
