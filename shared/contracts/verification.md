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
- final report records command, composition, hashes, and checks

## Merge

- every input is a recorded verified final
- order is explicit
- compatibility is checked before stream copy
- merged output receives independent full verification

A manual glance alone is insufficient. Automated checks alone are also insufficient for caption placement and creative quality.
