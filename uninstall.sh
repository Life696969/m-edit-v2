#!/usr/bin/env bash
set -euo pipefail
HOST=""
SCOPE="global"
PROJECT_DIR=""
LOCAL_HOME=""
PURGE=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --host) HOST="${2:-}"; shift 2 ;;
    --scope) SCOPE="${2:-}"; shift 2 ;;
    --project-dir) PROJECT_DIR="${2:-}"; shift 2 ;;
    --local-home) LOCAL_HOME="${2:-}"; shift 2 ;;
    --purge) PURGE=1; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$HOST" in claude|codex|agents|all) ;; *) echo "--host must be claude, codex, agents, or all" >&2; exit 2 ;; esac
case "$SCOPE" in global|project) ;; *) echo "--scope must be global or project" >&2; exit 2 ;; esac
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="${LOCAL_HOME:-$HOME}"
if [ "$SCOPE" = project ]; then PROJECT_DIR="${PROJECT_DIR:-$PWD}"; PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"; fi
paths() {
  case "$SCOPE:$1" in
    global:claude) echo "${CLAUDE_CONFIG_DIR:-$BASE/.claude}/skills|${CLAUDE_CONFIG_DIR:-$BASE/.claude}/commands" ;;
    global:codex) echo "${CODEX_HOME:-$BASE/.codex}/skills|" ;;
    global:agents) echo "$BASE/.agents/skills|" ;;
    project:claude) echo "$PROJECT_DIR/.claude/skills|$PROJECT_DIR/.claude/commands" ;;
    project:codex|project:agents) echo "$PROJECT_DIR/.agents/skills|" ;;
  esac
}
remove_host() {
  local skills commands directory name
  IFS='|' read -r skills commands <<<"$(paths "$1")"
  for directory in "$SOURCE"/skills/*; do
    name="$(basename "$directory")"
    rm -rf "$skills/$name"
  done
  if [ -n "$commands" ]; then rm -f "$commands/m_edit.md"; fi
}
if [ "$HOST" = all ]; then remove_host claude; remove_host codex; remove_host agents; else remove_host "$HOST"; fi
if [ "$PURGE" -eq 1 ]; then
  if [ "$SCOPE" = global ]; then rm -rf "$BASE/.m-edit"; else rm -rf "$PROJECT_DIR/.m-edit-suite"; fi
fi
echo "m-edit uninstalled ($SCOPE scope). Project .m-edit state was not removed."
