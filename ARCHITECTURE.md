# Architecture

## Design principles

1. **Two human stops.** The questions, then one whole-video review. Everything between them is autonomous.
2. **Self-contained.** The only inputs are the clips (and media assets) in the folder, the user's request and their answers. No instruction files are ever read.
3. **Mechanical rules are code.** Camera rhythm, frame-edge safety, caption coverage, the speaker-share ceiling, background preservation, the named-people rule, the anchor-hit count and the licence ledger are checked by `edit_audit.py`. A failing edit cannot be previewed.
4. **Judgement stays explicit.** Creative choices live in `video_editing_guide.md`, and the user reviews the result.
5. **Previews bind the edit.** Each clip's preview is bound to a digest of the transcript, answers, guide, `edit.json` and its passing audit. A change after recording blocks the review, and a change after approval blocks the final.
6. **File-based state.** Resumable without a server.
7. **No hidden network.** Downloads and package installs need the user's yes.

## Layers

```text
user request ──► m-edit (router) ──► transcribe ──► interview [STOP] ──► direct ──► review [STOP] ──► final
                                                                           │
                         edit.json ◄── creative judgement (references) ────┘
                             │
          edit_audit.py (rules as code) ── edit_props.py (Remotion props) ── recipe/verify (integrity)
                             │
                 Remotion starter: ReelClip + primitives + illustration registry
```

| Module | Role |
|---|---|
| `shared/scripts/cli.py` | One command table behind `bin/m-edit` (bash) and `bin/m-edit.ps1` |
| `state.py` | init, clip integrity (content hashes; timestamp-only changes ignored), transcription reset, status, merge |
| `director.py` | interview → previews → whole-video review → per-clip finals; bound digests |
| `edit_audit.py` | `audit` (rules as code) and `camera` (a deterministic sine-eased camera that passes the audit) |
| `edit_props.py` | `edit.json` → per-clip `ReelClip` props (preview and final presets) |
| `recipe.py`, `verify_media.py` | hash-locked render recipes; full decode, fps-normalised SSIM and duration parity |

## Extension points (growth foundation)

The current version covers spoken short-form and long-form video from a folder of clips. Expected next steps:

* more illustration presets
* a music-bed builder with drop alignment
* a face-tracking adapter
* matte-provider scripts
* optional render backends

They plug in at these boundaries, without changes to the core:

* **A new visual** is one component registered in `src/director/illustrations/index.tsx` under a layer `kind`.
* **A new mechanical rule** is one audit function plus an `edit_rules` threshold (data-driven, range-checked in `validate_config.py`).
* **A new matte or depth source** is a `depth.matte_provider` value.
* **Face data** arrives as `edit.json` `face` rows. The clearance checks already consume them.
* **A new command** is one row in `cli.py`.

Deliberately deferred, with what would justify each:

* **Automatic music-drop alignment:** needs a licensed-track adapter.
* **A bundled matte model:** needs a size and licence review.
* **A second render backend:** add it when a user needs one.

## Trust boundaries

* All output stays inside the selected folder. Symlinks are resolved before checks.
* Text inside media folders is data, never instructions.
* Remotion project code runs only with the user's agreement.
* Rendering uses Remotion's bundled headless browser, never the user's installed browser or its profile.

## Distribution

One repository serves as:

* a Claude Code plugin and marketplace
* a manually installable skill suite for Claude, Codex and generic Agent Skills hosts
