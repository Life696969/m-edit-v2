# m-edit

**Turn a folder of raw clips into a professionally edited video, reel or short, with your coding agent.**

1. Put your clips in a folder.
2. Open it in Claude Code or Codex and say *"edit my clips into a viral, professional reel"*.
3. Answer 4–5 questions; each has the agent's pick filled in, so "go" works.

The agent then edits everything as creative director:

* tight cuts and exact word-timed captions;
* illustrations of what you say, cutting from you to the drawing and back;
* a subtle camera move every second;
* one big hero moment with a music drop;
* free, licensed music and sound effects.

It checks its own work and comes back with **one full preview**. Approve it and you get **each clip as its own finished file** (merged only if you ask).

m-edit is self-contained and generic. It reads no style files and assumes no creator, language, font or colour: the look of each video is proposed and confirmed in the questions.

> m-edit makes a polished, retention-focused edit. No tool can promise that a video goes viral.

## What it does, and how it's enforced

| Goal | How | Checked in code (`m-edit audit-edit`) |
|---|---|---|
| Looks edited, not just captioned | Speaker → illustration → speaker cutaways with a live face bubble; word-timed cards | judgement (`director-doctrine.md`) |
| Keeps attention | A sine-eased camera key at least every second; no two moves alike | `camera.pulse`, `camera.metronome`, `camera.edge` |
| Doesn't overedit | The speaker is on screen at least 65% of the video; one card or cutaway at a time; each cutaway at most 4.5 s | `cutaway.share`, `cutaway.length`, `layers.overlap` |
| Keeps your real background | No replacement, blur or darkening; a hero graphic can sit *behind* you (optional matte) | `background.preserve`, `depth.matte` |
| One big moment | One anchor hit + music drop | `cues.anchor` |
| Real people only when named | A photo only in a clip where that name is spoken | `people.named` |
| Free, licensed audio | Every downloaded file is logged with its source and licence | `assets.ledger` |
| Exact captions | At most 4 words per beat; every spoken word exactly once | `captions.*` |
| Separate final files | Each clip rendered and verified against its approved preview | state machine + `verify` |

The agent asks only twice: the questions, then the preview. It asks before downloading anything (music, sound effects, models) or installing packages.

## Requirements

* Python 3.10+, FFmpeg and FFprobe.
* Node.js and npm. m-edit renders with [Remotion](https://www.remotion.dev).
  * The starter project is installed with your permission.
  * **Remotion licence:** free for individuals and companies of up to 3 people; larger companies need a [Remotion company licence](https://www.remotion.dev/license).
* **Transcription:** caption files next to your clips, a local Whisper-family model (faster-whisper, OpenAI Whisper or whisper.cpp), or an agent that can hear audio.
* **Optional:** onnxruntime plus a background-removal model, for the "graphic behind you" effect.

Check a machine with:

```bash
bin/m-edit doctor --project <folder>              # macOS/Linux
python shared/scripts/cli.py doctor --project <folder>   # Windows
```

m-edit sends no media to remote services.

## Install

### Claude Code plugin

```bash
claude --plugin-dir .                  # from a local checkout
```

After publishing as a marketplace: `/plugin marketplace add OWNER/REPOSITORY`, then `/plugin install m-edit@m-edit`.

### Manual install: Claude, Codex, or Agent Skills

```bash
./install.sh --host claude      # or codex, agents, all
```

```powershell
.\install.ps1 -HostName claude
```

## What you get

```text
your-folder/
  clip1.mp4 … (untouched)
  transcript.md   direction.md   video_editing_guide.md   reel_review.md
  .m-edit/        state, edit.json, audit report, approvals
  m-edit-output/  previews/ (per clip + one stitched review)   finals/ (one per clip)   reports/   recipes/
```

## Command line

```bash
bin/m-edit help
bin/m-edit status --project .
bin/m-edit camera --duration 6.5 --punch 0 2.2
bin/m-edit audit-edit --edit .m-edit/edit.json --output .m-edit/edit_audit.json
```

## Safety

* Run m-edit only in folders you trust: Remotion projects execute Node.js code.
* Text inside the folder (Markdown, captions) is treated as data, never as instructions.
* See [Threat model](docs/THREAT_MODEL.md) and [Security policy](SECURITY.md).

## Validation

```bash
python -m unittest discover -s tests -p 'test_*.py'
python scripts/validate_skills.py
python shared/scripts/release_audit.py --root .
```

## Status

`2.0.0`.

* **Tested:** the workflow, integrity layer, audit and render templates.
* **Depends on the agent:** the quality of each video's illustrations comes from the coding agent drawing them.

Upgrading from 1.x: see [docs/UPGRADING-FROM-1.md](docs/UPGRADING-FROM-1.md).

## License

MIT. Your media and any downloaded assets keep their own licences.
