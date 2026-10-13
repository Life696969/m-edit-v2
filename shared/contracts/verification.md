# Verification contract

Verification is evidence, not a success claim.

## Preview

- file exists and is non-empty
- expected video stream and duration are present
- required audio is present
- all streams decode without error
- dimensions/FPS match the guide
- representative frames are inspected through stills or a contact sheet
- captions are reviewed at normal speed for wording, timing, line breaks, collisions, and safe zones
- render recipe verifies against current code/data/assets

## Final

All preview checks plus:

- rendered from source masters and approved recipe
- expected codec/container/dimensions/audio
- duration parity with the approved preview
- visual-fidelity comparison against the approved preview meets the configured SSIM threshold
- no changed code, props, captions, package lock, or assets since preview approval
- clean delivery (unless the user explicitly opted out): `m-edit deliver-clean` passed **both** rounds for exactly this file, and `mark-reel-final` received its `delivery_check.json`. The checks: no extra tags, no forbidden boxes (`udta`/`meta`/`free`/`skip`/`uuid`/`btrt`), `ftyp mp42`, `colr nclx`, short `esds`, non-zero times, no encoder or tool strings and no SEI user data; AAC-LC 48 kHz stereo encoded once at ≥ 320k; true peak ≤ −1 dBTP; no full-scale samples; the voice alone under the limiter ceiling; limiter ≤ 1 dB; SNR ≥ 18 dB against the intended mix; lag ≤ 1 sample against the mix and the original recording; 0 decode errors and per-frame video hashes identical to the render
- final report records command, composition, hashes, and checks

## Merge

- every input is a recorded verified final
- order is explicit
- compatibility is checked before stream copy
- merged output receives independent full verification

A manual glance alone is insufficient. Automated checks alone are also insufficient for caption placement and creative quality.
