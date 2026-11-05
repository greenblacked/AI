#!/usr/bin/env bash
# Report a "## Waiver" heading written into a slice stage file that may not be waived. The
# FAMILY workflow lets only Architect (decision.md) and Launch (launch.md) be waived, in
# writing; Frame, Make, Inspect and Yield are always done. A waiver heading in frame.md,
# plan.md, inspect.md or yield.md is a skipped gate written down as if it were a decision.
# Deterministic: standard tools only, no network, no secrets, nothing run from the file.
#
# What it checks. For a written file whose path is docs/slices/<one segment>/frame.md,
# plan.md, inspect.md or yield.md, the file is read from disk at tool_input.file_path, so an
# Edit is judged on the whole file and not on its fragment. A line that is exactly
# "## Waiver" (a trailing space, tab or carriage return is ignored) makes the hook exit 2 and
# name the file and the line. decision.md, launch.md, other names, other paths and files
# without that heading are allowed.
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the
#     model, which can fix the file; the hook cannot undo anything.
#   - Only the exact heading is read. "### Waiver", "## Waived", an indented heading or a
#     waiver written in prose is not found, and a heading inside a fenced code block, such as
#     a quoted template, is found and reported.
#   - A docs/slices/ folder that means something else in a project gets the same check.
#   - Only the file on disk after the write is judged, never a shell command that creates
#     one. A file over 1 MiB is refused, not scanned.
set -Eeuo pipefail
export LC_ALL=C

input="$(cat)"
file=""
# Either parser prints nothing, and the hook allows, for input it cannot read a path from:
# invalid JSON, a non-object, a missing tool_input or a path that is not a string.
if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.file_path | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | python3 -I -c \
    'import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
value = tool.get("file_path") if isinstance(tool, dict) else None
print(value if isinstance(value, str) else "")' || true)"
fi

# Neither parser present, or no path: allow, because a hook that blocks everything on a
# missing tool is worse than no hook.
[ -n "$file" ] || exit 0

# docs/slices/<one segment>/<non-waivable stage>.md. The slice folder is the parent of the file
# and docs/slices its parent, compared whole, so a deeper path or a lookalike such as
# mydocs/slices/ stays out. A case pattern would let a star cross slashes.
case "${file##*/}" in
  frame.md | plan.md | inspect.md | yield.md) ;;
  *) exit 0 ;;
esac
case "$file" in
  */*) ;;
  *) exit 0 ;;
esac
slice_dir="${file%/*}"
slice_name="${slice_dir##*/}"
[ -n "$slice_name" ] || exit 0
case "$slice_dir" in
  */*) ;;
  *) exit 0 ;;
esac
slices_dir="${slice_dir%/*}"
case "$slices_dir" in
  docs/slices | */docs/slices) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the file for a waiver heading yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to check it for a waiver heading. Check the file is readable, then retry." >&2
  exit 2
fi
# No real stage file is near this size. The scan below is linear, so the limit bounds the
# work; a hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. A stage file is far smaller; check what was written to it." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; only the
# first two are an answer. A file with no "## Waiver" prefix has nothing to judge.
rc=0
grep -q '^## Waiver' <"$file" || rc=$?
case "$rc" in
  0) ;;
  1) exit 0 ;;
  *)
    echo "blocked: could not read $file to check it for a waiver heading. Check the file is readable, then retry." >&2
    exit 2
    ;;
esac

# One awk pass: a prefix compare per line, then an anchored match on the rest of the line.
# awk prints a last line, @@done, so that an awk that did not run (killed, or the redirection
# failed) is told from one that found nothing wrong. On a finding it prints the line number
# of the first heading.
rc=0
verdict="$(
  awk '
    substr($0, 1, 9) == "## Waiver" && substr($0, 10) ~ /^[ \t\r]*$/ {
      if (!first) first = NR
    }
    END {
      if (first) printf "%d\n", first
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for a waiver heading (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
finding="${verdict%@@done}"
finding="${finding%$'\n'}"

if [ -n "$finding" ]; then
  {
    echo "blocked: ${file##*/} has a \"## Waiver\" heading, and only decision.md (Architect) and launch.md (Launch) may be waived. The write already happened; remove the waiver and do the stage, or list what was not done under \"Not assessed\"."
    printf '%s:%s\n' "$file" "$finding"
  } >&2
  exit 2
fi
exit 0
