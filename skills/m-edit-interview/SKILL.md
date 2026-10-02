---
name: m-edit-interview
description: Use when an m-edit project has its transcript but no answered direction, or the editing direction (exact words, biggest moment, look, music, permissions) is undecided before an autonomous edit.
license: MIT
compatibility: Requires the m-edit CLI and read access to the project's transcript.
metadata:
  version: "2.0.0"
---

# Ask 4–5 questions, once

**Resolve `<suite-root>` first:** `${CLAUDE_PLUGIN_ROOT}` when it contains `shared/`; otherwise `${M_EDIT_HOME}/current`; otherwise the nearest `.m-edit-suite/current`; otherwise `~/.m-edit/current`.

Read `shared/references/direction-interview.md`.

* Send **one message** with **4–5 numbered questions**, between `direction.min_questions` and `direction.max_questions`.
* Each question carries your proposed answer, so the user can reply "go".
* Ask fewer than 4 only when the request genuinely leaves nothing more to decide.

## Build the message

1. Decide what the user's request and the clips already settle. Do not ask about those.
2. Fill the core questions in this order:
   1. words that must be exact
   2. the biggest moment
   3. the proposed look and music vibe
   4. permissions (fold them into one question)
3. Add structure or output only when needed.
4. Write `direction.md` from `shared/templates/direction.template.md`, with the questions exactly as you will send them.
5. Record the stop, then send the message:

```bash
m-edit await-direction --project "<folder>"
```

## STOP

Wait for the reply. When it arrives:

1. Paste it verbatim under `## Answers` and fill `## Decisions`.
2. Record it:

```bash
m-edit record-direction --project "<folder>" --evidence "<exact reply>"
```

3. Continue with `m-edit-direct` in the same turn. Make every remaining creative decision yourself.
