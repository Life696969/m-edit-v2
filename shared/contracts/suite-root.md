# Suite-root resolution

Resolve `<suite-root>` once, in this order:

1. `${CLAUDE_PLUGIN_ROOT}` when it exists and contains `shared/`.
2. `${M_EDIT_HOME}/current` when `M_EDIT_HOME` is set.
3. The nearest `.m-edit-suite/current` found from the selected project upward.
4. `~/.m-edit/current`.

Before using the suite, confirm that `<suite-root>/VERSION`, `shared/scripts/state.py`, and `shared/contracts/state-machine.md` exist. If none of the locations is valid, stop with installation guidance rather than guessing paths.

Prefer `<suite-root>/bin/m-edit` as the command entry point. On Windows, use `<suite-root>/bin/m-edit.ps1` or invoke the Python scripts directly.
