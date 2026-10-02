# Thin wrapper: every command is routed by shared/scripts/cli.py (one table for bash and PowerShell).
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
& python (Join-Path $Root "shared/scripts/cli.py") @args
exit $LASTEXITCODE
