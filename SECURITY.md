# Security policy

## Supported versions

Security fixes are applied to the latest release candidate or stable release.

## Reporting

Do not publish exploitable path, installer, command-execution, prompt-injection, or source-overwrite vulnerabilities before maintainers have a chance to respond. Use GitHub private vulnerability reporting when enabled. Otherwise open a minimal issue asking for a private contact channel without including exploit details.

## Scope

Relevant issues include:

- paths escaping the selected project folder
- source media overwritten by generated output
- stale approvals surviving changed protected artifacts
- installer replacement or rollback vulnerabilities
- secrets or personal data included in public releases
- unexpected network access
- unsafe command construction

m-edit cannot sandbox an untrusted Remotion/Node project or coding agent. That limitation is documented rather than treated as a vulnerability.
