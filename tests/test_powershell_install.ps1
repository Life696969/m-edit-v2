$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TempHome = Join-Path ([IO.Path]::GetTempPath()) ("m-edit-pwsh-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $TempHome | Out-Null
try {
  & (Join-Path $Root 'install.ps1') -HostName all -LocalHome $TempHome
  $Expected = @(
    '.claude/skills/m-edit/SKILL.md',
    '.codex/skills/m-edit/SKILL.md',
    '.agents/skills/m-edit/SKILL.md',
    '.claude/commands/m_edit.md',
    '.m-edit/current/shared/scripts/state.py'
  )
  foreach ($Relative in $Expected) {
    $Path = Join-Path $TempHome $Relative
    if (-not (Test-Path $Path)) { throw "Missing installed path: $Relative" }
  }
  & (Join-Path $Root 'uninstall.ps1') -HostName all -LocalHome $TempHome
  if (Test-Path (Join-Path $TempHome '.claude/skills/m-edit')) { throw 'Claude skill was not removed' }
  if (-not (Test-Path (Join-Path $TempHome '.m-edit/current'))) { throw 'Release data should remain without -Purge' }
  & (Join-Path $Root 'uninstall.ps1') -HostName all -LocalHome $TempHome -Purge
  if (Test-Path (Join-Path $TempHome '.m-edit')) { throw 'Purge did not remove suite release data' }
  Write-Host 'PowerShell install/uninstall smoke test passed'
} finally {
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $TempHome
}
