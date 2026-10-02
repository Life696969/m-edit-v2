# Customization

m-edit is self-contained.

* **The look of each video** is decided in the 4–5 questions: the agent proposes, you confirm or change.
* **No style files:** m-edit reads no Markdown or style files from your folders. Your preferences stay in your head (or your replies), never in the skill.

## Settings (`.m-edit/config.json`, created on first run)

| Setting | Default | Effect |
|---|---|---|
| `direction.min_questions` / `max_questions` | 4 / 5 | How many questions are asked up front |
| `edit_rules.camera_pulse_seconds` | 1.0 | A subtle camera move at least this often |
| `edit_rules.camera_scale_min` / `max` | 1.03 / 1.075 | How subtle the camera stays |
| `edit_rules.cutaway_share_max` | 0.35 | You stay on screen at least 65% of the video |
| `edit_rules.cutaway_max_seconds` | 4.5 | The longest time away from you |
| `edit_rules.max_caption_words` | 4 | Words per caption beat |
| `edit_rules.max_anchor_hits` | 1 | One biggest sound |
| `edit_rules.background` | `preserve` | `allow-replace` permits background replacement |
| `edit_rules.people_require_spoken_name` | true | A real person's photo only where they are named |
| `depth.matte_provider` | `none` | `rvm-onnx` or `precomputed` enables "graphic behind you" |
| `assets.allow_free_licensed_downloads` | false | Pre-approve free, licensed music and SFX downloads |
| `render.renderer_timeout_ms` / `retry_concurrency` | 240000 / 1 | For heavy 4K renders on low-memory machines |

**Fixed invariants:**

* There is always one preview review before finals.
* Finals are always separate files.
* Merging is always on request only.
