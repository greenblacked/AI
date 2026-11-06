#!/usr/bin/env bash
# Report a written stylesheet that sets width, min-width or max-width to a bare 100vw. The
# viewport width includes the scrollbar, so the element is wider than the space the page has
# and the page scrolls sideways. The same finding the distinctive-page-design lint reports as
# floor-viewport-width. Deterministic: standard tools only, no network, no secrets, nothing
# run from the file.
#
# What it checks. For a written file whose path ends in .css, the file is read from disk at
# tool_input.file_path, so an Edit is judged on the whole file and not on its fragment. A
# line with a width, min-width or max-width declaration whose whole value is 100vw (or 100dvw,
# 100svw, 100lvw, optionally followed by !important) is a finding, and the hook exits 2 with
# the file and line of up to five of them, with a fixed message and no text from the file. A file that holds the full-bleed idiom,
# calc(50% - 50vw) in either order, is allowed whole: that idiom is paired with a 100vw band
# on purpose.
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the
#     model, which can fix the file; the hook cannot undo anything.
#   - A declaration is read as one line. A value split across lines, a width inside a comment
#     or a string, and a width set through a custom property or inside calc(), min(), max()
#     or clamp() are not judged: only a value that is exactly 100vw is.
#   - The full-bleed exemption covers the whole file, so one deliberate band hides a stray
#     100vw elsewhere in it. The lint reports that case.
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

case "$file" in
  *.css) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check for a 100vw width yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to check it for a 100vw width. Check the file is readable, then retry." >&2
  exit 2
fi
# No hand-written stylesheet is near this size. The scan below is linear, so the limit bounds
# the work; a hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. Check what was written to it, or lint it with page_lint.py." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; only the
# first two are an answer. A full-bleed stylesheet is allowed whole.
rc=0
grep -Eiq '50%[[:space:]]*-[[:space:]]*50[dsl]?vw|-50[dsl]?vw[[:space:]]*\+[[:space:]]*50%' <"$file" || rc=$?
case "$rc" in
  0) exit 0 ;;
  1) ;;
  *)
    echo "blocked: could not read $file to check it for a 100vw width. Check the file is readable, then retry." >&2
    exit 2
    ;;
esac

# One awk pass, one match per line, no backtracking. The leading group makes "line-width" or
# "xmin-width" a different property; the trailing semicolon added to the line stands in for an
# end-of-line anchor. awk prints a last line, @@done, so that an awk that did not run (killed,
# or the redirection failed) is told from one that found nothing wrong.
rc=0
verdict="$(
  awk '
    {
      line = tolower($0)
      gsub(/\r/, "", line)
      line = line ";"
      if (match(line, /(^|[^a-z0-9_-])((min|max)-)?width[ \t]*:[ \t]*100[dsl]?vw[ \t]*(!important[ \t]*)?[;}]/)) {
        if (++n <= 5) printf "%d:width set to a bare 100vw\n", NR
      }
    }
    END { print "@@done" }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for a 100vw width (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
findings="${verdict%@@done}"
findings="${findings%$'\n'}"

if [ -n "$findings" ]; then
  {
    echo "blocked: $file sets a width to a bare 100vw, which includes the scrollbar and makes the page scroll sideways. The write already happened; fix it now."
    printf '%s\n' "$findings" | while IFS= read -r row; do
      printf '%s:%s\n' "$file" "$row"
    done
    echo "Use 100% instead. For a full-bleed band, keep the container at 100% and offset it with margin-inline: calc(50% - 50vw)."
  } >&2
  exit 2
fi
exit 0
