# Public release checklist

## Completed in this build

- [x] Deterministic tests pass locally.
- [x] Skill metadata and trigger-description validation pass.
- [x] Default configuration and fixed safety invariants validate.
- [x] Release audit passes.
- [x] Optional external private denylist audit passes.
- [x] No personal or client style, example or preference is bundled.
- [x] No raw media, rendered media, screenshots, transcripts, binaries, caches, or archives are included in the source package.
- [x] No committed credential, token, email address, absolute user path, or build path is present.
- [x] Default config and the bundled Remotion starter are generic.
- [x] Shell installation, project installation, upgrade protection, backups, dry run, and uninstall are tested.
- [x] Deterministic ZIP and SHA-256 output are tested.
- [x] README, architecture, threat model, security policy, contribution guide, changelog, and release process are present.

## Required before stable `1.0.0`

- [ ] GitHub CI passes on Linux, macOS, and Windows.
- [ ] PowerShell smoke test passes on Windows.
- [ ] Black-box Claude Code and Codex pressure evals pass.
- [ ] Bundled Remotion starter installs, type-checks, opens, and renders on clean machines.
- [ ] Representative real-video field tests pass across content modes.
- [ ] Claude plugin and marketplace validation pass.
- [ ] Stable release notes include retained test/eval artifacts.
