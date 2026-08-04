#!/usr/bin/env bash
# Symlink every skill in this repository into ~/.claude/skills.
#
# Installing through the plugin marketplace is the better route for other people —
# it namespaces the skills and updates with the repository. This script exists for
# the author's own machine, where editing a skill and having the change live
# immediately is worth more than the namespacing.
set -Eeuo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly TARGET_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

DRY_RUN=0
FORCE=0

usage() {
  cat <<'USAGE'
Usage: install.sh [--dry-run] [--force]

  --dry-run   Print what would change without touching the filesystem.
  --force     Replace an existing entry even when it is not a symlink to this repo.

Environment:
  CLAUDE_SKILLS_DIR  Install location (default: ~/.claude/skills)
USAGE
}

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
die() { log "error: $*"; exit 1; }

while (($# > 0)); do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    -h | --help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

[[ -d "$REPO_ROOT/skills" ]] || die "no skills/ directory under $REPO_ROOT"

if ((DRY_RUN == 0)); then
  mkdir -p "$TARGET_DIR"
fi

linked=0
skipped=0

while IFS= read -r -d '' skill_md; do
  skill_dir="$(dirname "$skill_md")"
  name="$(basename "$skill_dir")"
  link="$TARGET_DIR/$name"

  if [[ -L "$link" ]]; then
    current="$(readlink "$link")"
    if [[ "$current" == "$skill_dir" ]]; then
      skipped=$((skipped + 1))
      continue
    fi
  elif [[ -e "$link" ]] && ((FORCE == 0)); then
    log "skipping $name: $link exists and is not a symlink into this repository (use --force)"
    skipped=$((skipped + 1))
    continue
  fi

  if ((DRY_RUN == 1)); then
    log "would link $name -> $skill_dir"
  else
    ln -sfn "$skill_dir" "$link"
    log "linked $name"
  fi
  linked=$((linked + 1))
done < <(find "$REPO_ROOT/skills" -name SKILL.md -print0 | sort -z)

log "done: $linked linked, $skipped unchanged or skipped"
((DRY_RUN == 1)) && log "dry run - nothing was written"
exit 0
