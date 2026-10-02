# Troubleshooting

## Skill cannot find the suite

Check `CLAUDE_PLUGIN_ROOT`, `M_EDIT_HOME`, project `.m-edit-suite/current`, or `~/.m-edit/current`. Run the installer again and confirm `VERSION` plus `shared/scripts/state.py` exist.

## No clips found

Confirm supported video extensions and that clips are not under `.m-edit`, output folders, `node_modules`, `dist`, or `build`.

## Context changed

A source clip or the config changed after the questions were answered. The edit restarts from transcription. This is intentional.

## Final blocked after an approved preview

The preview, guide, recipe, code, caption data, props, assets, or package lock changed. Render and approve a new preview.

## SSIM comparison fails

First confirm final and preview use the same composition, timing, props, crop, and assets. Lower the threshold only when an intentional delivery transform makes the comparison unsuitable, and document the reason.

## No transcription provider

Provide adjacent captions, install a local provider, configure a local model, or use a host with genuine audio inspection.

## FFmpeg timeout

Increase `verification.ffmpeg_timeout_seconds` for long media after confirming the input is trusted.
