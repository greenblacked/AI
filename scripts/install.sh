#!/usr/bin/env bash
# Symlink every skill in this repository into ~/.claude/skills.
#
# Installing through the plugin marketplace is the better route for normal use — it
# namespaces the skills and updates with the repository. This script is for working on
# the skills themselves, where editing one and having the change live immediately is
# worth more than the namespacing.
set -Eeuo pipefail

readonly REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly TARGET_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

DRY_RUN=0
FORCE=0

usage() {
  cat <<'USAGE'
Usage: install.sh [--dry-run] [--force]

  --dry-run   Print what would change without touching the filesystem.
  --force     Replace an existing symlink or file that does not point into this
              repository. A real directory is never removed - remove it yourself.

Environment:
  CLAUDE_SKILLS_DIR  Install location (default: ~/.claude/skills)

Exit codes:
  0  every skill is linked
  2  bad usage
  3  finished, but at least one skill was skipped because something was in the way
USAGE
}

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
die() { log "error: $*"; exit 1; }

# Canonicalise a directory to the physical path `cd`+`pwd -P` resolves it to, rather than
# `realpath`/`readlink -f` - neither is guaranteed present or consistent across GNU and
# BSD. Empty output (a dangling target, or one that is not a directory) compares unequal
# to everything, which is the right answer: a broken link is still a conflict.
resolved_dir() { (cd "$1" 2>/dev/null && pwd -P); }

# A symlink's recorded target, resolved the way the kernel would follow it: `readlink`
# returns exactly what was written, which is relative to the link's own directory when
# it is not already absolute.
resolved_link() { (cd "$(dirname "$1")" && cd "$(readlink "$1")" 2>/dev/null && pwd -P); }

while (($# > 0)); do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    -h | --help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

[[ -d "$REPO_ROOT/plugins" ]] || die "no plugins/ directory under $REPO_ROOT"

if ((DRY_RUN == 0)); then
  mkdir -p "$TARGET_DIR"
fi

linked=0
skipped=0
conflicts=0

while IFS= read -r -d '' skill_md; do
  skill_dir="$(dirname "$skill_md")"
  name="$(basename "$skill_dir")"
  link="$TARGET_DIR/$name"

  if [[ -L "$link" ]]; then
    current="$(readlink "$link")"
    # Compared as resolved, physical paths rather than as strings: a correct link
    # reached through a symlinked alias - REPO_ROOT itself sitting behind one, most
    # commonly - has a different spelling but the same target, and a string compare
    # reported that as a conflict. Resolved once into a variable: it is a subshell plus
    # a `cd`, and nothing about the link changes between the emptiness check and the
    # comparison that follows it. `|| true`: a dangling target makes the resolution
    # fail, and under `set -e` an assignment's own exit status would otherwise end the
    # whole script rather than simply leaving this one comparison unequal.
    current_resolved="$(resolved_link "$link")" || true
    if [[ -n "$current_resolved" && "$current_resolved" == "$(resolved_dir "$skill_dir")" ]]; then
      skipped=$((skipped + 1))
      continue
    fi
    if ((FORCE == 0)); then
      # A symlink pointing somewhere else is somebody's deliberate arrangement - their
      # own working copy, most likely. Replacing it silently is the one outcome nobody
      # would want from an install script, and the help already promises --force here.
      log "skipping $name: $link points at $current (use --force)"
      skipped=$((skipped + 1))
      conflicts=$((conflicts + 1))
      continue
    fi
  elif [[ -d "$link" && ! -L "$link" ]]; then
    # `ln -sfn` onto a real directory creates the link *inside* it, which leaves the
    # skill uninstalled while the script reports success. Removing a directory of
    # unknown contents is not something a convenience script should do on its own, so
    # this is a conflict even under --force.
    log "skipping $name: $link is a directory; remove it yourself if you want it replaced"
    skipped=$((skipped + 1))
    conflicts=$((conflicts + 1))
    continue
  elif [[ -e "$link" ]] && ((FORCE == 0)); then
    log "skipping $name: $link exists and is not a symlink into this repository (use --force)"
    skipped=$((skipped + 1))
    conflicts=$((conflicts + 1))
    continue
  fi

  if ((DRY_RUN == 1)); then
    log "would link $name -> $skill_dir"
  else
    # Remove first rather than relying on -f: the target may be a stale symlink or a
    # regular file, and replacing it in place keeps the outcome unambiguous.
    rm -f "$link"
    ln -sfn "$skill_dir" "$link"
    log "linked $name"
  fi
  linked=$((linked + 1))
done < <(find "$REPO_ROOT/plugins" -name SKILL.md -print0 | sort -z)

log "done: $linked linked, $skipped unchanged or skipped"
((DRY_RUN == 1)) && log "dry run - nothing was written"
((conflicts > 0)) && exit 3
exit 0
