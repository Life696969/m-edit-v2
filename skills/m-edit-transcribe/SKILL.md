---
name: m-edit-transcribe
description: Use when an m-edit project's clips have no transcript yet, the spoken audio needs timestamped transcription, or source clips or config changed and the transcript must be refreshed before the editing questions.
license: MIT
compatibility: Requires media inspection capability or a local transcription provider.
metadata:
  version: "2.0.0"
---

# Transcribe, then go straight to the questions

**Resolve `<suite-root>` first:** `${CLAUDE_PLUGIN_ROOT}` when it contains `shared/`; otherwise `${M_EDIT_HOME}/current`; otherwise the nearest `.m-edit-suite/current`; otherwise `~/.m-edit/current`.

This phase inspects and documents media. It creates no edit, preview or final.

Read `shared/references/transcription.md` and `shared/references/captions.md`. Then:

```bash
m-edit begin-transcription --project "<folder>"
m-edit transcribe detect
```

## Transcription sources, in order

1. Caption files the user put next to the clips (`.srt`, `.vtt`, compatible `.json`).
2. A local Whisper-family provider via `m-edit transcribe run --project "<folder>" --clip "<clip>" --output ".m-edit/transcripts/<clip-stem>.json"`, with word timestamps.
3. The host agent's genuine audio inspection.

* **Model download:** if transcription is only possible by downloading a model, ask for that one permission now and STOP until the user answers. It is the only stop allowed before the questions.
* **Honesty:** never claim to have heard audio you cannot inspect, and never invent words. Mark uncertainty as `[unclear]`.

## Write `transcript.md`

Use `shared/templates/transcript.template.md`. For every clip include:

* the filename and duration
* visual notes
* phrase timestamps
* the exact spoken words, in the speaker's own language
* uncertain words

Score doubtful names, numbers and keywords against the audio where a local model allows it, for example by force-decoding the alternatives and comparing log-probabilities. Carry the uncertain ones into the questions.

## Continue

Use `m-edit-interview` now, in the same turn.
