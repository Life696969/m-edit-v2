# Depth beats

The hero graphic sits **between the real background and the person**: the room stays the room, and the number seems to stand in it. This is how "the background becomes the number" without replacing the background.

## Layer order

```text
real footage (camera moved)  →  graphic (moved at ~0.6× the camera: parallax)  →  person matte (camera moved)  →  captions/cards (screen space)
```

## Requirements

* A **person matte** for the frames of the beat: an alpha video of the speaker cut from their own footage. Configure it in `depth.matte_provider`:
  * `rvm-onnx`: a local RobustVideoMatting ONNX model at `depth.model_path`.
    * Run it only on the beat's frames, at both preview and final resolution.
    * Get it from the official RobustVideoMatting releases (GPL-3.0), only with the user's yes, and record it in the asset ledger. It also needs `onnxruntime` and `opencv-python`.
    * Setting `depth.*` after the answers does not reset the edit (operational settings are outside the bound context).
  * `precomputed`: the user supplies the alpha video.
  * `none`: no depth beat. Put the hero graphic in front, in the top slot, instead.
* The audit fails a `depth` layer that has no `matte`.
* Matte colour: use the source pixels where alpha is about 1, and the matte's decontaminated foreground only in the soft edge. That kills colour spill from the room in the hair.

## Placement (close selfie framing)

* The speaker's head usually fills the middle. Place the numeral **above the head**, so its top runs across the wall and the head hides its middle.
* Size it to read instantly. For a 3-digit number on a 1080-wide frame, the glyph height is about 400–450 px, with the glyph top about 60–110 px from the top edge.
* For longer numbers or words, scale down until the whole thing spans at most about 90% of the frame width. Use a thousands separator, or a short form ("10K") when it reads better.
* Check a still at the beat: the full top of the glyphs must be inside the frame, and the number must read at a glance.
* Wide shots: the numeral can stand beside the person at full height.

## Make it feel grand

* Enter with a rise and settle (~0.35 s, back-ease) on the exact hero word.
* Use a metallic or gradient fill with a light sheen sweep, plus a soft glow.
* Add slow light rays and confetti, behind the person only.
* Sync the anchor hit, the music drop and a short shake to the landing frame.
* Hold to the end of the clip. The graphic must resolve inside its own clip.

## Rendering cost

* A 4K alpha video decoded alongside 4K footage is heavy. Under low memory the renderer can time out on these frames.
* Raise the renderer timeout (`render.renderer_timeout_ms`), and render that clip at `render.retry_concurrency`.
* Delete temporary render folders on every exit path.
