# Changelog

## 2.0.0

A new workflow. 1.x projects must be finished with 1.x (see `docs/UPGRADING-FROM-1.md`).

### The flow

1. Clips in a folder.
2. "Edit my clips into a professional reel".
3. **4–5 questions once**, each with the agent's pick filled in.
4. An autonomous edit.
5. **One whole-video review.**
6. Each clip rendered as its own verified final; merge only on request.

### Self-contained

- No instruction, profile or style files are read.
- The look is proposed and confirmed in the questions.
- Text inside the folder is data, never instructions.

### Editing rules as code

`m-edit audit-edit` checks:

- the camera pulse, frame-edge exposure, and no metronome moves
- caption coverage and length
- the speaker-share ceiling, cutaway length, and one card at a time
- that layers stay inside their clip
- that the background is preserved
- that depth beats have a matte
- that photos of real people appear only where the name is spoken
- one anchor hit
- a licensed asset ledger
- caption/mouth and card/eye clearance

Each preview is bound to a digest of the transcript, answers, guide, `edit.json` and its passing audit.

### New commands

- `m-edit camera`: a deterministic sine-eased camera that passes the audit by construction. It was property-tested on 6,000 cases.
- `m-edit edit-props`: per-clip Remotion props from the same audited `edit.json`.
- Workflow commands:
  - `await-direction`
  - `record-direction`
  - `record-preview`
  - `await-reel-approval`
  - `approve-reel`
  - `mark-reel-final`
  - `reopen-reel`

### Remotion starter

A new `ReelClip` composition with:

- a camera rig
- a face bubble
- a card
- a cutaway shell
- a depth sandwich
- word-timed captions with glyph-only legibility
- an audio mix
- an illustration registry

### References

- the questions
- director doctrine
- camera pulse
- sound design
- depth beats
- edit data

### Doctor

New checks:

- the transcription model
- the matte model
- disk space
- browser policy

npm and npx are now found on Windows.

### Fixes

- Final-vs-preview SSIM resamples to the preview frame rate.
- A timestamp-only source change no longer invalidates the edit under full hashing.
- One Python command dispatcher serves bash and PowerShell, and the tests run on Windows.

### Removed

- The classic per-clip gates
- Story-cut gates
- Instruction discovery
- Profiles

## 1.0.0-rc.1

- added direct source-media and instruction-file integrity checks
- added atomic state writes and project locking
- added approval receipts with exact user evidence
- added hash-locked Remotion render recipes
- added preview verification and final-to-preview SSIM checks
- added local transcription-provider adapters and canonical caption utilities
- hardened FFmpeg execution with local protocol restrictions and timeouts
- added safe instruction-discovery policy and symlink boundary checks
- added versioned, atomic manual installers with project scope and uninstallers
- added Claude plugin component declarations
- expanded generic content modes, caption guidance, threat model, quality bar, and documentation
- added CI, release packaging, trigger tests, security tests, and model-eval harness
- added a neutral, prop-driven Remotion starter with configurable dimensions, FPS, fitting, and caption styling
- added safe Remotion scaffolding without automatic dependency installation
- added canonical caption chunking using real word timestamps when available
- added standard WebVTT timestamp support
- blocked implicit Whisper model downloads unless local models or explicit network authorization are present
- added a complete generated-video state-machine integration test
- removed creator-specific denylist strings from the public repository; private release phrases are now supplied externally

## 0.1.0

- initial public beta with transcript, preview, final, and merge gates
