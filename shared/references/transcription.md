# Transcription system

Transcribe every discovered source clip separately before editing.

## Accuracy

- Preserve spoken language and wording.
- Use phrase-level timestamps accurate enough for cuts and caption synchronization; word timestamps are preferred when available.
- Mark uncertain audio as `[unclear]`; never guess silently.
- Preserve false starts, repetition, interruptions, and unfinished phrases in the raw clip transcript. Suggest removals separately.
- Verify names, products, acronyms, numbers, and factual claims when possible.
- Do not claim to have listened when the host lacks audio inspection.

## Provider order

1. user-provided or adjacent caption/transcript files
2. configured local Whisper provider
3. genuine host-agent audio inspection

Do not download a model or send audio to a remote service without authorization. Record which provider produced each canonical transcript and any language/model setting.

## Visual notes

For each clip record framing, speaker position, faces, gestures, props, screens, camera movement, meaningful actions, empty space, focus changes, continuity, and areas that captions/graphics must not cover.

## Combined transcript

Propose the most likely order without rewriting spoken words. Label opening, setup, body, proof, demonstration, transition, ending, and call to action when present. Separate certainty from inference.

## Review output

End with uncertain words, names/claims needing verification, possible false starts, and order assumptions. Then continue straight to the questions (`m-edit-interview`). Those end the transcription phase; there is no separate transcript stop.
