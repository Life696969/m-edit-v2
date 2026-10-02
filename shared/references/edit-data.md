# Edit data (`edit.json`)

`edit.json` is the single contract between creative judgement, the audit and the renderer.

* It lives at `.m-edit/edit.json`.
* Remotion props are generated from it, one per clip.
* `m-edit audit-edit` checks it.
* A director preview can only be recorded when the audit report passed on the **current** file.

Times are clip-local seconds. Positions are fractions of the canvas.

```json
{
  "schema_version": 1,
  "canvas": {"width": 1080, "height": 1920, "fps": 30},
  "rules": {"camera_pulse_seconds": 1.0},
  "assets": [
    {"id": "boom", "path": "public/sfx/boom.wav", "kind": "sfx", "source": "user-provided file: boom.wav", "license": "user's own file"},
    {"id": "bed", "path": "public/audio/bed.wav", "kind": "music", "source": "https://example.org/track/123", "license": "Pixabay Content License"},
    {"id": "ceo", "path": "public/img/ceo.jpg", "kind": "photo", "person": "Jane Doe", "source": "press kit URL", "license": "press use"}
  ],
  "clips": [
    {
      "id": "clip1.mp4",
      "duration": 6.5,
      "words": [{"t": "Today", "s": 0.0, "e": 0.44}],
      "chunks": [{"words": [0, 1, 2], "hl": [2], "big": true, "y": 0.705}],
      "camera": {"origin": [0.5, 0.36], "keys": [{"t": 0.0, "s": 1.04, "x": 0.001, "y": -0.002}],
                 "shakes": [{"t": 4.22, "dur": 0.3, "amp": 4.5}]},
      "layers": [
        {"id": "workflow", "type": "card", "s": 0.72, "e": 3.94, "box": [64, 200, 1016, 370]},
        {"id": "hundred", "type": "depth", "s": 4.16, "e": 6.5, "matte": "p1.webm"},
        {"id": "folder", "type": "cutaway", "s": 2.8, "e": 5.4}
      ],
      "cues": [{"at": 4.22, "asset": "boom", "role": "anchor"}],
      "face": [{"t": 0.0, "eye": 0.37, "mouth": 0.55, "chin": 0.62}]
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `words` | The exact spoken words with timestamps (from forced alignment). Captions index into this list and never retype it. |
| `chunks` | Caption beats: word indices, highlighted indices, `big` for punch lines, and optional `y` (centre, fraction of height) and `size_px`. |
| `camera` | Origin (the transform origin, near the face) and sine-eased keys from `m-edit camera`. Shakes are in px. |
| `layers` | Types are `cutaway`, `broll` (full frame, counted against the speaker's share), `card` (opaque panel; `box` in px for the eye-clearance check), `depth` (needs `matte`), `photo`, `logo`, `overlay` and `text`. `background-replace` is only allowed when `edit_rules.background` is `allow-replace`. Any layer may reference an `asset`. |
| `cues` | Sound placements. `role` is one of `anchor`, `transition`, `stamp`, `slide` or `ui`. Every `asset` must be in the ledger. |
| `face` | Optional tracked rows: eye, mouth and chin as fractions of the source height. They enable the caption/mouth and card/eye checks. |

The renderer is free to carry extra fields: illustration beats, highlight colours, card variants. The audit ignores fields it does not know.
