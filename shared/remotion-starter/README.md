# Bundled Remotion starter

This starter is intentionally neutral. It renders one video with optional canonical m-edit caption segments and exposes all visual choices through props. It does not install dependencies automatically.

After scaffolding and explicit authorization for package installation:

```bash
npm install
npm run studio
```

Copy or link trusted media into `public/m-edit-assets/` and use a project-relative path in input props. Include the complete `src/`, props JSON, caption JSON, source asset, and lockfile in the preview render recipe.

Copy `props.example.json`, set source metadata and caption data, and pass it to Remotion with `--props`. Width, height, FPS, fit, caption position, typography, colors, and background are all props rather than fixed creator defaults.

## m-edit: `ReelClip`

`ReelClip` renders **one clip** of a director edit. Its props come from the audited `.m-edit/edit.json`:

```bash
m-edit edit-props --edit .m-edit/edit.json --clip clip1.mp4 --preset preview --output props/clip1-preview.json
npx remotion render src/index.ts ReelClip out/clip1-preview.mp4 --props=props/clip1-preview.json
```

Layers in it:

* footage under the camera pulse
* an optional depth beat (graphic between the room and the person matte)
* at most one card or full-frame cutaway, with a live face pip
* word-timed captions in screen space
* voice, music bed and cues

Illustrations are bespoke per video. Write one component per visual, and register it in `src/director/illustrations/index.tsx` under the `kind` that `edit.json` layers reference. The core composition never changes. `steps` and `label` are working examples.
