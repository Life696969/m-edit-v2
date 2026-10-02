# Caption system

Captions must make speech easier to understand without obscuring the video or changing the speaker's meaning.

## Source contract

- Use the approved transcript exactly unless the user explicitly requests rewritten on-screen copy.
- Preserve the original language, script, punctuation intent, names, numbers, and personality.
- Do not silently translate, sanitize, summarize, or “improve” spoken wording.
- User corrections become the new transcript source of truth and invalidate downstream work.
- Keep raw transcript data separate from display chunks so visual line breaks never rewrite content.

## Canonical data

Prefer one canonical JSON source with millisecond timestamps. Validate it with `m-edit captions validate`. Store display chunk timing, optional word timing, emphasis spans, and placement overrides as data rather than hardcoded component branches.

## Chunking and line breaks

Chunk by meaning, breath, and reading rhythm, not a universal word count.

- Prefer one short phrase at a time and no more than two lines unless the format demands otherwise.
- Keep names, numbers, articles, prepositions, and dependent phrases together.
- Break at natural syntax boundaries.
- Avoid orphaned one-character/one-word lines unless intentionally emphatic.
- Do not show long full sentences on fast short-form video.
- Strong single words may receive a separate beat only when it improves comprehension or emotional timing.
- For CJK, RTL, or scripts without space-delimited words, use script-aware segmentation and correct text direction.

## Synchronization

- Enter with the spoken phrase and leave after it can be read.
- Never lead the speech unless the creative guide explicitly uses anticipation.
- Word highlighting may follow speech but must not flicker, race, or lag distractingly.
- Convert timestamps to frames with one tested helper.
- Account for source trims, speed changes, pauses, and nested sequences.
- Review at normal speed, muted, and with audio.

## Placement and collision handling

Detect faces, mouths, hands, demonstrated controls, products, lower thirds, and platform UI-safe regions. Choose a stable base zone, then move captions only when content requires it.

- Maintain edge margins and line-height breathing room.
- Never cover critical tutorial UI or meaningful action.
- Avoid rapid position jumping; transition placement intentionally.
- Use scene-specific placement overrides when automatic rules fail.
- Test representative frames with the longest line, smallest frame, and busiest background.

## Readability and accessibility

- Use contrast that works against the actual frame, not a blank design canvas.
- Prefer a restrained shadow, stroke, gradient, blur, or subtle background treatment over large opaque boxes.
- Size type for the target resolution and viewing distance.
- Do not rely on color alone for emphasis.
- Respect reduced-motion intent when the project calls for it.
- Avoid flashing, constant bouncing, and per-word effects that compete with comprehension.
- Preserve emoji and special characters only when the chosen font supports them; otherwise select a compatible fallback.

## Emphasis

Highlight only words that improve hierarchy, meaning, or emotional timing. Use a coherent combination of weight, size, color, position, or timing. Do not emphasize every noun or animate every word.

## Quality checks

Before approval, verify:

- exact wording against the approved transcript
- no missing or duplicated phrases
- timestamps and trims align
- line breaks are natural
- no face/UI/action collisions
- safe margins at target dimensions
- no unsupported glyphs or clipped text
- readable contrast across representative frames
- consistent style across clips

## In m-edit

* **The source of truth** is the transcript as confirmed by the direction answers, plus any corrections made at review. There is no separate transcript approval.
* **Script:** captions use the script the speaker writes in, not whatever script a transcriber happens to output. Transcribers often write mixed-language or romanized speech in a different script.
  * Use the script the user writes their request in, and confirm it in the "words that must be exact" question.
  * Keep the words, never translate.
* **Background preserved** (`edit_rules.background = preserve`): legibility comes only from the glyphs themselves. Use a thick stroke, a tight shadow, heavier type, or a cleaner position. Never use a blur, a gradient, a darkened band or a box behind captions.
