# Host support

## Claude Code

Use the plugin marketplace for the best installation/update experience. Manual installation also copies skills and the `/m_edit` alias.

## Codex

Manual installation places skills in `~/.codex/skills/` globally or `.agents/skills/` for a project-local install. Invoke `$m-edit` or ask Codex to use m-edit.

## Generic Agent Skills

Install to `~/.agents/skills/`. The host must support filesystem/shell execution for the full workflow.

Tool-use reliability varies by model and host. Deterministic guard scripts reduce, but do not eliminate, instruction-following risk.
