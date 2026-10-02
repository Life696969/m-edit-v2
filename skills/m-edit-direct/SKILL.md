---
name: m-edit-direct
description: Use when an m-edit project has answered direction and the whole video must be cut, illustrated, sound-designed, audited and previewed as a professionally edited video, or when the user asks for changes to that preview.
license: MIT
compatibility: Requires FFmpeg/FFprobe, Remotion (an existing project or the bundled starter) and the m-edit CLI.
metadata:
  version: "2.0.0"
---

# Direct the edit

**Resolve `<suite-root>` first:** `${CLAUDE_PLUGIN_ROOT}` when it contains `shared/`; otherwise `${M_EDIT_HOME}/current`; otherwise the nearest `.m-edit-suite/current`; otherwise `~/.m-edit/current`. Run `m-edit` as `<suite-root>/bin/m-edit`, `<suite-root>/bin/m-edit.ps1`, or `python <suite-root>/shared/scripts/cli.py`.

You are the creative director. Work autonomously from the answered direction to one whole-video review. Ask nothing else unless proceeding is impossible.

## Read first

* `direction.md`
* `transcript.md`
* the clips
* `shared/references/director-doctrine.md`
* `shared/references/camera-pulse.md`
* `shared/references/sound-design.md`
* `shared/references/depth-beats.md` (only for a depth hero moment)
* `shared/references/edit-data.md`
* `shared/references/captions.md`
* `shared/contracts/external-assets.md`
* `shared/contracts/remotion-execution.md`

## Build, in this order

1. **Cut.**
   * Trim dead air, false starts and verbatim repeats at clip boundaries.
   * Inside a clip, cut a pause only when it is longer than about 0.4 s and is not a deliberate beat. Make it a jump cut with an instant camera reframe.
   * Rearrange only what the answers approved.
   * List every removal for the review report.
2. **Exact words.** Get word timestamps on the trimmed audio: `m-edit transcribe run` with word timestamps, or forced alignment of the confirmed text with a local Whisper-family model. Use the confirmed spellings and the agreed script.
3. **Guide.** Write `video_editing_guide.md` from the template:
   * the spine
   * the hero moment
   * a speaker → illustration → speaker table per clip
   * the cards
   * the camera punch words
   * the music arc and cue list
   * the asset ledger
   * what is deliberately not done
4. **Edit data.** Write `.m-edit/edit.json`, with `src.preview` and `src.final` per clip. Generate each clip's camera with `m-edit camera`. Add tracked face rows when a tracker is available.
5. **Audit until it passes.** A preview cannot be recorded otherwise.

```bash
m-edit audit-edit --edit "<folder>/.m-edit/edit.json" --output "<folder>/.m-edit/edit_audit.json" --config "<folder>/.m-edit/config.json"
```

6. **Render.** Use `m-edit scaffold-remotion` and `npm install`, but only with the editor permission from the questions. Run an existing Remotion project in the folder only if the user agreed.
   * Register one illustration per visual in `src/director/illustrations/index.tsx`. Draw what is said, timed to the word.
   * Generate props per clip with `m-edit edit-props --preset preview`.
   * Render stills of risky frames first: the hero, the densest card, the busiest cutaway.
7. **Preview every clip.** For each clip:
   1. Render the preview.
   2. Run `m-edit verify --contact-sheet ...`.
   3. Run `m-edit recipe create`, with `--include` covering the Remotion `src/`, `.m-edit/edit.json` and the assets folder.
   4. Record it:

```bash
m-edit record-preview --project "<folder>" --clip "<clip>" --path "<preview>" --recipe "<recipe>" --verification "<verification>"
```

8. **Self-review before showing anything.** Read every contact sheet and fix, re-render and re-record anything with:
   * an empty stage at the start of a cutaway
   * wrapped or clipped text
   * a graphic touching the frame edge
   * a caption over the mouth
   * an illustration that does not match its words
   * a dead stretch
   * overediting: two things fighting for one beat, decoration that doesn't match the words, or no clean face moments

   Check loudness (about −14 to −15 LUFS), true peak (at most −1 dBTP) and A/V sync.
9. **Review package.** Make one stitched review file (review only; the finals stay separate) and write `reel_review.md` from the template. Then:

```bash
m-edit await-reel-approval --project "<folder>" --review "<stitched review file>"
```

## STOP

Show the review file and `reel_review.md`, then wait.

* **A change request:** revise, re-audit, re-render only the affected clips, record them, request the review again, and STOP.
* **Approval:** use `m-edit-final`.

## Render resilience

* Never launch the user's installed browser. Remotion uses its own headless shell.
* Check free disk space before long renders. Delete temporary render folders on every exit path.
* A renderer timeout on heavy frames: raise `render.renderer_timeout_ms` and retry that clip at `render.retry_concurrency`.
* A transient "No frame found" compositor error: retry the clip once at concurrency 1.
