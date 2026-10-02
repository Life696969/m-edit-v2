#!/usr/bin/env bash
set -euo pipefail

HOST=""
SCOPE="global"
PROJECT_DIR=""
LOCAL_HOME=""
FORCE=0
DRY_RUN=0

usage() {
  cat <<'USAGE'
Usage: ./install.sh --host claude|codex|agents|all [options]

Options:
  --scope global|project   Install for the user or current repository (default: global)
  --project-dir DIR        Project root for project scope (default: current directory)
  --local-home DIR         Override HOME for testing or isolated installation
  --force                  Re-stage the same version and replace existing m-edit skills
  --dry-run                Print destinations without writing
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host) HOST="${2:-}"; shift 2 ;;
    --scope) SCOPE="${2:-}"; shift 2 ;;
    --project-dir) PROJECT_DIR="${2:-}"; shift 2 ;;
    --local-home) LOCAL_HOME="${2:-}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$HOST" in claude|codex|agents|all) ;; *) echo "--host must be claude, codex, agents, or all" >&2; exit 2 ;; esac
case "$SCOPE" in global|project) ;; *) echo "--scope must be global or project" >&2; exit 2 ;; esac

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for required in VERSION skills shared bin/m-edit; do
  [ -e "$SOURCE/$required" ] || { echo "Incomplete m-edit checkout: missing $required" >&2; exit 1; }
done
VERSION="$(tr -d '[:space:]' < "$SOURCE/VERSION")"
case "$VERSION" in ''|*[!A-Za-z0-9._-]*) echo "Invalid VERSION value" >&2; exit 1 ;; esac
BASE="${LOCAL_HOME:-$HOME}"

if [ "$SCOPE" = "global" ]; then
  SUITE_BASE="$BASE/.m-edit"
else
  PROJECT_DIR="${PROJECT_DIR:-$PWD}"
  PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
  SUITE_BASE="$PROJECT_DIR/.m-edit-suite"
fi
RELEASES="$SUITE_BASE/releases"
RELEASE="$RELEASES/$VERSION"
CURRENT="$SUITE_BASE/current"
BACKUPS="$SUITE_BASE/backups/$(date -u +%Y%m%dT%H%M%SZ)-$$"

run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '+ '; printf '%q ' "$@"; printf '\n'
  else
    "$@"
  fi
}

install_release() {
  if [ -e "$RELEASE" ] && [ "$FORCE" -ne 1 ]; then
    echo "Release $VERSION already exists at $RELEASE (use --force to replace)" >&2
    exit 1
  fi
  local temp="$RELEASES/.${VERSION}.tmp.$$"
  local old="$RELEASES/.${VERSION}.old.$$"
  run mkdir -p "$RELEASES"
  run rm -rf "$temp" "$old"
  run cp -R "$SOURCE" "$temp"
  run rm -rf "$temp/.git" "$temp/dist" "$temp/build" "$temp/.m-edit" "$temp/.m-edit-suite"
  run find "$temp" -type d -name __pycache__ -prune -exec rm -rf '{}' +
  run find "$temp" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
  if [ "$DRY_RUN" -eq 0 ]; then
    if [ -e "$RELEASE" ]; then mv "$RELEASE" "$old"; fi
    if mv "$temp" "$RELEASE"; then
      rm -rf "$old"
    else
      [ -e "$old" ] && mv "$old" "$RELEASE"
      rm -rf "$temp"
      echo "Failed to activate release; previous release restored" >&2
      exit 1
    fi
    local current_temp="$SUITE_BASE/.current.tmp.$$"
    rm -f "$current_temp"
    ln -s "$RELEASE" "$current_temp"
    if ! mv -f "$current_temp" "$CURRENT" 2>/dev/null; then
      rm -rf "$CURRENT"
      mv "$current_temp" "$CURRENT"
    fi
  else
    echo "+ atomically activate $RELEASE and point $CURRENT to it"
  fi
}

host_paths() {
  local host="$1"
  if [ "$SCOPE" = "global" ]; then
    case "$host" in
      claude) echo "${CLAUDE_CONFIG_DIR:-$BASE/.claude}/skills|${CLAUDE_CONFIG_DIR:-$BASE/.claude}/commands" ;;
      codex) echo "${CODEX_HOME:-$BASE/.codex}/skills|" ;;
      agents) echo "$BASE/.agents/skills|" ;;
    esac
  else
    case "$host" in
      claude) echo "$PROJECT_DIR/.claude/skills|$PROJECT_DIR/.claude/commands" ;;
      codex|agents) echo "$PROJECT_DIR/.agents/skills|" ;;
    esac
  fi
}

replace_directory() {
  local staged="$1" target="$2" old="$3"
  rm -rf "$old"
  if [ -e "$target" ]; then mv "$target" "$old"; fi
  if mv "$staged" "$target"; then
    rm -rf "$old"
  else
    [ -e "$old" ] && mv "$old" "$target"
    rm -rf "$staged"
    echo "Failed to install $target; previous version restored" >&2
    return 1
  fi
}

install_host() {
  local host="$1"
  local paths skills commands
  paths="$(host_paths "$host")"
  skills="${paths%%|*}"
  commands="${paths#*|}"
  run mkdir -p "$skills" "$BACKUPS/$host"
  for directory in "$RELEASE"/skills/*; do
    local name target staged old
    name="$(basename "$directory")"
    target="$skills/$name"
    staged="$skills/.${name}.new.$$"
    old="$skills/.${name}.old.$$"
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "+ atomically install $directory -> $target"
      continue
    fi
    [ -e "$target" ] && cp -R "$target" "$BACKUPS/$host/$name"
    rm -rf "$staged" "$old"
    cp -R "$directory" "$staged"
    replace_directory "$staged" "$target" "$old"
  done
  if [ -n "$commands" ]; then
    run mkdir -p "$commands"
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "+ atomically install Claude command alias -> $commands/m_edit.md"
    else
      [ -e "$commands/m_edit.md" ] && cp "$commands/m_edit.md" "$BACKUPS/$host/m_edit.md"
      cp "$RELEASE/commands/m_edit.md" "$commands/.m_edit.md.new.$$"
      mv -f "$commands/.m_edit.md.new.$$" "$commands/m_edit.md"
    fi
  fi
  echo "Installed $host skills to $skills"
}

install_release
if [ "$HOST" = "all" ]; then
  install_host claude
  install_host codex
  install_host agents
else
  install_host "$HOST"
fi

if [ "$DRY_RUN" -eq 0 ]; then
  chmod +x "$CURRENT/bin/m-edit" "$CURRENT/shared/scripts/"*.py "$CURRENT/scripts/"*.py "$CURRENT/evals/"*.py 2>/dev/null || true
fi
cat <<SUMMARY
m-edit $VERSION installed.
Suite: $CURRENT
Scope: $SCOPE
Run the coding agent in a trusted video project and invoke m-edit.
SUMMARY
