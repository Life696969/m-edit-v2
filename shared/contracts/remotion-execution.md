# Remotion-execution contract

1. Inspect the existing project before creating, upgrading, or installing anything.
2. Use current official Remotion guidance when available; do not vendor stale API knowledge as authority.
3. Keep source media immutable and referenced by path.
4. Store transcript/caption timing as data separate from visual components.
5. Use `useCurrentFrame()`, composition FPS, deterministic interpolation/springs, and seeded randomness only.
6. Avoid browser time, CSS transitions, network calls during render, and nondeterministic layout.
7. Centralize timestamp-to-frame conversion and account for trims, offsets, speed changes, and nested sequences.
8. Keep assets local at render time. Record external sources and usage rights.
9. Create a hash-locked render recipe before preview approval. Include the entry point, relevant source tree, caption data, props, assets, source clip, package lock, composition ID, and command/template.
10. Render finals from source masters and the approved recipe, never by transcoding the preview.
11. Do not upgrade dependencies or scaffold a project without user authorization.
12. Keep final delivery differences limited to approved encoding/resolution settings.
