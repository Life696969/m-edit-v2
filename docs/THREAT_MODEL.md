# Threat model

The authoritative operational rules are in `shared/contracts/threat-model.md`.

m-edit assumes the selected workspace is trusted enough to read and run. It reduces accidental damage and stale approval reuse, but it does not sandbox Node.js, FFmpeg, Python, or the coding agent.

Use narrow filesystem permissions, review package scripts, keep network access disabled unless needed, and do not run untrusted Remotion projects.
