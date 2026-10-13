# Validation status

Version: `2.1.0`

Validated locally on August 1, 2026 in a Linux environment with Python 3.13, Node.js 22, npm 10, and FFmpeg 7.

## 2.1.0: validated locally on 2026-10-13

Windows 11, Python 3.13, FFmpeg 8.1, numpy.

* **The full suite passes:** 70 tests, 5 skipped as before (the bash-installer and POSIX-only tests skip on Windows).
* **Clean delivery** (`tests/test_delivery.py`, 11 tests):
  * a dirty render fails every metadata check, and the scrub passes with identical decoded samples;
  * a one-clip project passes both rounds with 0 lag, a gain-only voice-safe level, ≥ 18 dB SNR and a bit-exact video;
  * `standard` is quieter than `voice-safe`, and neither lets the voice reach the ceiling;
  * an undershooting AAC encode is redone from the lossless mix;
  * a dual-mono mix is warned, not refused;
  * lossy audio is never re-encoded;
  * a phone frame rate (~29.92 fps) keeps every frame;
  * `mark-reel-final` accepts only a passing two-round report for exactly the final, unless the user opted out.
* **Real footage:** a 6 s phone recording (hot: −8.3 LUFS, peaks above 0 dBFS) with a real music bed and two library SFX passed both rounds. Voice gain only (−2.18 dB, voice-safe), −10.49 LUFS, true peak −1.7 dBTP, limiter 0.0 dB, SNR 50.9 dB, lag 0/0, 180/180 frames bit-exact, AAC-LC 320 kbps, no tags beyond brand/language/neutral handlers.
* **Release audit** and **skill validation** pass.
* **Not yet done:** a full m-edit edit run through `m-edit-final` by an agent on real footage; macOS/Linux runs of the delivery tests.

## 2.0.0: validated locally on 2026-10-02

Windows 11, Python 3.13, FFmpeg 8.1 and Node 24.

* **The full unit and integration suite passes on Windows.** It covers:
  * an end-to-end run on generated video: two user stops, individual finals and an explicit merge;
  * invalidation after a change following approval;
  * a revision during review;
  * a source change resetting the answers;
  * a timestamp-only touch not invalidating;
  * path-escape and source-overwrite rejection;
  * evidence being required;
  * a 1.x project being refused with guidance;
  * a style file in the folder being ignored.
* **The edit audit** has a unit test for every rule. The camera generator was property-tested on 6,000 random cases with zero findings.
* **The `ReelClip` starter:**
  * typechecks (`tsc --noEmit`);
  * renders stills and a full 6 s clip from an audited `edit.json` through `edit-props`.
* **SSIM** of a 4K/60 fps final against its 1080p/30 fps preview: 0.996.
* **Agent behaviour test:** the same request against 1.x and 2.0. 1.x needed ~15 user replies and asked no direction questions; 2.0 needed 2 replies and asked the questions once.
* **Not yet done:** a real-footage end-to-end edit with 2.0; Claude marketplace install; macOS/Linux runs.

## Passed locally (1.0.0-rc.1)

- 46 deterministic unit and integration tests across workflow, captions, transcription, instruction discovery, installers, recipes, media verification, scaffold generation, trigger descriptions, sanitization, and packaging
- complete generated-video workflow from initialization through transcript approval, guide recording, preview recipe, preview approval, final-to-preview comparison, and `all_clips_complete`
- full source-content hashing and direct instruction-file hashing
- source-content mutation blocking without false invalidation from timestamp-only changes under full hashing
- atomic state writes and project lock behavior
- exact approval receipts for transcript, story cut, preview, continuation, and merge
- wrong-clip, path-traversal, sibling-folder, and symlink-boundary rejection
- preview, guide, caption/code/asset recipe, and final drift blocking
- all-stream FFmpeg decode, dimension/audio checks, contact sheets, duration parity, and SSIM comparison
- SRT, standard WebVTT, common JSON, word-timestamp chunking, validation, and SRT export
- offline-first transcription behavior; no implicit model download
- neutral Remotion scaffold creation without package installation
- global and project-local shell installation, same-version protection, force backup, dry run, and uninstall preservation
- Agent Skills metadata, trigger descriptions, independent suite-root bootstrap, and explicit STOP markers
- deterministic ZIP creation and checksum generation
- generic secret/path/binary audit plus an optional external private denylist
- a private release audit using an uncommitted denylist for creator-specific material; no matches remained

## Prepared for CI, not executed in this environment

- Python 3.10 and 3.13 matrix on Linux, macOS, and Windows
- PowerShell installer and uninstaller smoke test on Windows
- deterministic release packaging after all platform tests
- tagged GitHub release workflow

## Evidence still required before calling stable behavior “10/10”

- black-box pressure evaluations on real Claude Code and Codex installations
- successful edits of representative talking-head, tutorial, podcast/interview, product-demo, montage, slideshow, story-cut, and mixed-format projects
- actual `npm install`, TypeScript compile, Remotion Studio, preview render, and final render of the bundled starter on supported platforms
- Claude plugin validation and marketplace install/update test
- official Agent Skills validator run when available in the release environment
- Windows PowerShell execution, which could not be run in this Linux environment

The repository is release-engineered as a strong public release candidate. Stable `1.0.0` should be cut only after the empirical items above pass and their reports are attached.
