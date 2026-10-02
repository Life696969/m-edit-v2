param(
  [Parameter(Mandatory=$true)] [ValidateSet("claude","codex","agents","all")] [string]$HostName,
  [ValidateSet("global","project")] [string]$Scope = "global",
  [string]$ProjectDir = "",
  [string]$LocalHome = "",
  [switch]$Purge
)
$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Base = if ($LocalHome) { [IO.Path]::GetFullPath($LocalHome) } else { $HOME }
if ($Scope -eq "project") { if (-not $ProjectDir) { $ProjectDir = (Get-Location).Path }; $ProjectDir = [IO.Path]::GetFullPath($ProjectDir) }
function Get-Paths([string]$HostValue) {
  if ($Scope -eq "global") {
    switch ($HostValue) {
      "claude" { $Config = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $Base ".claude" }; return @{ Skills = Join-Path $Config "skills"; Commands = Join-Path $Config "commands" } }
      "codex" { $Config = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $Base ".codex" }; return @{ Skills = Join-Path $Config "skills"; Commands = $null } }
      "agents" { return @{ Skills = Join-Path $Base ".agents/skills"; Commands = $null } }
    }
  } else {
    if ($HostValue -eq "claude") { return @{ Skills = Join-Path $ProjectDir ".claude/skills"; Commands = Join-Path $ProjectDir ".claude/commands" } }
    return @{ Skills = Join-Path $ProjectDir ".agents/skills"; Commands = $null }
  }
}
$Hosts = if ($HostName -eq "all") { @("claude","codex","agents") } else { @($HostName) }
foreach ($HostValue in $Hosts) {
  $Paths = Get-Paths $HostValue
  if (Test-Path $Paths.Skills) {
    Get-ChildItem -Directory (Join-Path $Source "skills") | ForEach-Object {
      Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Paths.Skills $_.Name)
    }
  }
  if ($Paths.Commands) { Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $Paths.Commands "m_edit.md") }
}
if ($Purge) {
  if ($Scope -eq "global") { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Base ".m-edit") }
  else { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $ProjectDir ".m-edit-suite") }
}
Write-Host "m-edit uninstalled ($Scope scope)."
