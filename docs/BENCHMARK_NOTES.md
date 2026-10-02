# Design benchmark notes

m-edit was designed after studying mature coding-agent workflow suites, while keeping video editing as its own domain rather than copying software-development roles.

## Patterns adopted

### From gstack

- a broad router plus phase-specific specialist skills
- host-aware installation instead of assuming one agent runtime
- deterministic preambles and status inspection before work
- reusable command-line tools for rules that should not depend on model memory

### From Superpowers

- mandatory workflows rather than optional advice
- approval checkpoints that stop immediately
- skill authoring treated like test-driven process design
- pressure scenarios and trigger-description tests
- verification before claiming completion

### From GSD

- file-based state that survives sessions
- thin orchestration with lazily loaded specialist context
- human-readable artifacts between phases
- explicit project boundaries and resumable phase routing

### From Remotion's official skills

- separate concerns for setup, captions, media handling, rendering, and API guidance
- Remotion-specific knowledge loaded only when the current phase needs it

### From the Agent Skills specification

- discoverable hyphenated names
- concise trigger-oriented descriptions
- progressive disclosure through `SKILL.md` plus supporting references and tools

## What m-edit adds for video work

- edit authorization bound to source-clip and config hashes
- one whole-video review before any final
- one-current-clip enforcement
- preview-bound render recipes that lock code, caption data, props, assets, source, and package lock
- final-to-preview visual fidelity checks
- generic caption normalization and chunking
- a neutral Remotion scaffold
- explicit merge authorization after verified individual finals

The goal is not to imitate the size of another suite. The goal is to apply the same discipline: clear routing, bounded context, mechanical enforcement, adversarial testing, and honest verification.
