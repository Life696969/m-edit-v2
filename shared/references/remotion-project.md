# Remotion project guidance

## Inspect before changing

Read `package.json`, lockfiles, Remotion version, entry points, compositions, schemas, fonts, reusable components, asset conventions, render scripts, TypeScript settings, and output paths. Run existing tests/type checks before changing code when practical.

## No project exists

Describe the scaffold and dependencies before creating them. Network access and package installation require user authorization. Keep the Remotion workspace separate from raw footage and generated delivery folders.

## Architecture

- Store transcript and caption timing in JSON/TypeScript data.
- Use typed props or a Zod schema for composition inputs.
- Keep design tokens and reusable caption/layout components centralized.
- Keep per-clip creative data declarative.
- Use a single timestamp-to-frame helper.
- Reference local assets deterministically.
- Avoid a monolithic component full of clip-specific conditionals.

## Timing and media

Use source metadata and composition FPS consistently. Handle trims, offsets, speed changes, transitions, and nested sequences explicitly. Preserve audio sync through every transform.

## Determinism

Use `useCurrentFrame()`, `interpolate()`, composition FPS, deterministic springs, and seeded randomness. Avoid `Date`, browser clocks, network requests, CSS transitions, or unseeded randomness during render.

## Preview/final parity

Create one render recipe before preview approval. It must identify the composition, entry point, input props, source clip, relevant source code/data/assets, package lock, and render command/template. Final rendering may change delivery quality but not the recipe's creative inputs.
