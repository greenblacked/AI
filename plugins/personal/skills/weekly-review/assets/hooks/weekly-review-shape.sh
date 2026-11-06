#!/usr/bin/env bash
# Report a written weekly review whose shape breaks the skill's own rule: not 3 to 5
# commitments, or no "Consciously not doing" section. A review with six commitments or no
# refusals has not chosen anything. Deterministic: standard tools only, no network, no
# secrets, nothing run from the file.
#
# What it checks. For a written .md file under a reviews/ directory, the file is read from
# disk at tool_input.file_path, so an Edit is judged on the whole file and not on its
# fragment. It applies only when the first non-empty line starts with "# Week of". Then the
# lines under the first "## Commitments" heading, up to the next line starting "## ", must
# hold 3 to 5 items (lines starting "N. " or "- "), and a line starting
# "## Consciously not doing" must exist. A finding exits 2 and names the file, the line and
# the count. Any other file is allowed.
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the
#     model, which can fix the file; the hook cannot undo anything.
#   - Headings and counts only. It cannot tell whether a commitment is checkable or a
#     reason is real, and a renamed heading is a finding.
#   - Items inside a fenced code block count, and an indented bullet or a wrapped item line
#     does not. A monthly or quarterly review does not start "# Week of" and is skipped.
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

# reviews/**/*.md. The slash before "reviews" keeps a directory such as myreviews/ out.
case "$file" in
  reviews/*.md | */reviews/*.md) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the review's shape yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to check the shape of the review. Check the file is readable, then retry." >&2
  exit 2
fi
# No weekly review is near this size. The scan below is linear, so the limit bounds the work;
# a hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. A weekly review is far smaller; check what was written to it." >&2
  exit 2
fi

# One awk pass, no backtracking. awk prints a last line, @@done, so that an awk that did not
# run (killed, or the redirection failed) is told from one that found nothing wrong. Each
# finding is "line:message"; a file whose first non-empty line is not "# Week of" has none.
rc=0
verdict="$(
  awk '
    { sub(/\r$/, "") }
    !started && $0 ~ /[^ \t]/ {
      started = 1
      first = NR
      if (substr($0, 1, 9) == "# Week of") week = 1
    }
    !week { next }
    substr($0, 1, 3) == "## " {
      if (insec) insec = 0
      if (!seen && substr($0, 1, 14) == "## Commitments") { seen = 1; insec = 1; at = NR; next }
      if (!notdoing && substr($0, 1, 24) == "## Consciously not doing") notdoing = 1
      next
    }
    insec && ($0 ~ /^[0-9]+\. / || substr($0, 1, 2) == "- ") { items++ }
    END {
      if (week) {
        if (!seen) printf "%d:no \"## Commitments\" section; a review holds 3 to 5\n", first
        else if (items < 3 || items > 5) printf "%d:\"## Commitments\" holds %d items; a review holds 3 to 5\n", at, items
        if (!notdoing) printf "%d:no \"## Consciously not doing\" section; each item needs a reason and a reconsider date\n", first
      }
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for the shape of the review (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
findings="${verdict%@@done}"
findings="${findings%$'\n'}"

if [ -n "$findings" ]; then
  {
    echo "blocked: $file is a weekly review that breaks the shape the weekly-review skill sets. The write already happened; fix the review now."
    printf '%s\n' "$findings" | while IFS= read -r line; do printf '%s:%s\n' "$file" "$line"; done
    echo "A review holds 3 to 5 checkable commitments and a Consciously not doing section with a reason and a reconsider date for each item."
  } >&2
  exit 2
fi
exit 0
