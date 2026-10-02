param(
  [Parameter(Mandatory=$true)] [ValidateSet("claude","codex","agents","all")] [string]$HostName,
  [ValidateSet("global","project")] [string]$Scope = "global",
  [string]$ProjectDir = "",
  [string]$LocalHome = "",
  [switch]$Force,
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Version = (Get-Content (Join-Path $Source "VERSION") -Raw).Trim()
$Base = if ($LocalHome) { [IO.Path]::GetFullPath($LocalHome) } else { $HOME }
if ($Scope -eq "project") {
  if (-not $ProjectDir) { $ProjectDir = (Get-Location).Path }
  $ProjectDir = [IO.Path]::GetFullPath($ProjectDir)
  $SuiteBase = Join-Path $ProjectDir ".m-edit-suite"
} else {
  $SuiteBase = Join-Path $Base ".m-edit"
}
$Releases = Join-Path $SuiteBase "releases"
$Release = Join-Path $Releases $Version
$Current = Join-Path $SuiteBase "current"
$Backup = Join-Path $SuiteBase ("backups/" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ"))

function Invoke-Write([scriptblock]$Action, [string]$Description) {
  if ($DryRun) { Write-Host "+ $Description" } else { & $Action }
}

if ((Test-Path $Release) -and -not $Force) { throw "Release $Version already exists at $Release. Use -Force to replace." }
Invoke-Write { New-Item -ItemType Directory -Force -Path $Releases | Out-Null } "create $Releases"
$Temp = Join-Path $Releases (".$Version.tmp." + $PID)
Invoke-Write { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Temp; Copy-Item -Recurse -Force $Source $Temp } "stage release"
Invoke-Write { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Temp ".git"), (Join-Path $Temp "dist"), (Join-Path $Temp "build"), (Join-Path $Temp ".m-edit"), (Join-Path $Temp ".m-edit-suite"); Get-ChildItem -Recurse -Directory $Temp -Filter __pycache__ | Remove-Item -Recurse -Force; Get-ChildItem -Recurse -File $Temp -Filter *.pyc | Remove-Item -Force } "remove repository and generated files"
Invoke-Write { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Release; Move-Item $Temp $Release } "activate release $Version"
Invoke-Write { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Current; Copy-Item -Recurse -Force $Release $Current } "update current release"

function Get-HostPaths([string]$HostValue) {
  if ($Scope -eq "global") {
    switch ($HostValue) {
      "claude" {
        $Config = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $Base ".claude" }
        return @{ Skills = Join-Path $Config "skills"; Commands = Join-Path $Config "commands" }
      }
      "codex" {
        $Config = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $Base ".codex" }
        return @{ Skills = Join-Path $Config "skills"; Commands = $null }
      }
      "agents" { return @{ Skills = Join-Path $Base ".agents/skills"; Commands = $null } }
    }
  } else {
    if ($HostValue -eq "claude") { return @{ Skills = Join-Path $ProjectDir ".claude/skills"; Commands = Join-Path $ProjectDir ".claude/commands" } }
    return @{ Skills = Join-Path $ProjectDir ".agents/skills"; Commands = $null }
  }
}

function Install-Host([string]$HostValue) {
  $Paths = Get-HostPaths $HostValue
  Invoke-Write { New-Item -ItemType Directory -Force -Path $Paths.Skills | Out-Null } "create $($Paths.Skills)"
  $HostBackup = Join-Path $Backup $HostValue
  Invoke-Write { New-Item -ItemType Directory -Force -Path $HostBackup | Out-Null } "create backup $HostBackup"
  Get-ChildItem -Directory (Join-Path $Release "skills") | ForEach-Object {
    $Target = Join-Path $Paths.Skills $_.Name
    $Stage = Join-Path $Paths.Skills ("." + $_.Name + ".tmp." + $PID)
    if (Test-Path $Target) { Invoke-Write { Copy-Item -Recurse -Force $Target (Join-Path $HostBackup $_.Name) } "backup $Target" }
    Invoke-Write { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Stage; Copy-Item -Recurse -Force $_.FullName $Stage; Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Target; Move-Item $Stage $Target } "install $($_.Name)"
  }
  if ($Paths.Commands) {
    Invoke-Write { New-Item -ItemType Directory -Force -Path $Paths.Commands | Out-Null; Copy-Item -Force (Join-Path $Release "commands/m_edit.md") (Join-Path $Paths.Commands "m_edit.md") } "install Claude command alias"
  }
  Write-Host "Installed $HostValue skills to $($Paths.Skills)"
}

$Hosts = if ($HostName -eq "all") { @("claude","codex","agents") } else { @($HostName) }
$Hosts | ForEach-Object { Install-Host $_ }
Write-Host "m-edit $Version installed. Suite: $Current"
