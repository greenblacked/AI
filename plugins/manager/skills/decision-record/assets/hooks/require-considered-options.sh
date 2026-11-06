#!/usr/bin/env bash
# Report a written decision record whose "## Considered Options" section lists fewer than two
# options, or that has no such section. A record naming one option is a rationalisation with a
# filename: it keeps the conclusion and loses the reasoning. Deterministic: standard tools only,
# no network, no secrets, nothing run from the file.
#
# What it checks. For a written file under docs/decisions/ or docs/adr/ (at any depth) whose
# name starts with a digit or "ADR-" and ends in .md, the file is read from disk at
# tool_input.file_path, so an Edit is judged on the whole file and not on its fragment. The
# line "## Considered Options" opens the section, the next line starting "# " or "## " closes
# it, and a list item is a line starting "* ", "- " or digits then ". " at column one. Fewer
# than two items, or no such heading, exits 2 and names the file and the heading line. A
# README.md or index in the same directory has no numbered name and is allowed.
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the
#     model, which can fix the file; the hook cannot undo anything.
#   - Options written as a table or as prose are not counted, so such a record gets a finding
#     that is safe to ignore. An indented sub-bullet is not an item.
#   - The template's placeholder bullets count, so this judges structure and not content: two
#     unfilled "[Option]" lines pass. A draft written before its options exist is flagged on
#     each write until they do.
#   - Records kept outside docs/decisions or docs/adr are not covered; the rule file's paths
#     and this script's patterns must change together. A heading inside a code fence is read
#     as a heading.
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

# docs/decisions/**/*.md and docs/adr/**/*.md. The slash before "docs" keeps a directory such
# as mydocs/ out.
case "$file" in
  */docs/decisions/*.md | docs/decisions/*.md | */docs/adr/*.md | docs/adr/*.md) ;;
  *) exit 0 ;;
esac
# NNNN-title.md or ADR-NNNN-title.md; an index or README beside the records is not a record.
case "${file##*/}" in
  [0-9]*.md | ADR-[0-9]*.md | adr-[0-9]*.md) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or count the considered options yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to count its considered options. Check the file is readable, then retry." >&2
  exit 2
fi
# No real decision record is near this size. The scan below is linear, so the limit bounds the
# work; a hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. A decision record is far smaller; check what was written to it." >&2
  exit 2
fi

# grep exits 0 or 1 once it has read the file (1 for an empty one) and 2 or more when it could
# not; only the first two mean the file can be scanned.
rc=0
grep -q '' <"$file" || rc=$?
if [ "$rc" -gt 1 ]; then
  echo "blocked: could not read $file to count its considered options. Check the file is readable, then retry." >&2
  exit 2
fi

# One awk pass, no backtracking: fixed-width prefix compares per line and anchored matches. The
# section opens at the first "## Considered Options" line (trailing blanks and CR allowed) and
# closes at the next "# " or "## " line. awk prints the heading line and the item count, or
# "none" when there is no heading, then @@done, so that an awk that did not run (killed, or the
# redirection failed) is told from one that found nothing wrong.
rc=0
verdict="$(
  awk '
    BEGIN { head = 0; open = 0; count = 0 }
    {
      if (open) {
        if (substr($0, 1, 2) == "# " || substr($0, 1, 3) == "## ") open = 0
        else if (substr($0, 1, 2) == "* " || substr($0, 1, 2) == "- ") count++
        else if (match($0, /^[0-9]+\. /)) count++
      } else if (!head && substr($0, 1, 21) == "## Considered Options") {
        if (match(substr($0, 22), /^[ \t\r]*$/)) { head = NR; open = 1 }
      }
    }
    END {
      if (!head) print "none"
      else print head ":" count
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for its considered options (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
finding="${verdict%@@done}"
finding="${finding%$'\n'}"

if [ "$finding" = "none" ]; then
  {
    echo "blocked: $file has no \"## Considered Options\" section, so it records a conclusion without the alternatives. The write already happened; add the section with at least two options, each with the reason it was rejected."
    printf '%s:1: no "## Considered Options" heading\n' "$file"
  } >&2
  exit 2
fi
count="${finding##*:}"
if [ "$count" -lt 2 ]; then
  {
    echo "blocked: $file lists $count considered option(s), and a record needs at least two. The write already happened; add the missing option now."
    printf '%s:%s: %s option(s) under "## Considered Options"\n' "$file" "${finding%%:*}" "$count"
    echo "Do nothing counts as an option and is often the honest runner-up. Options written as a table or as prose are not counted: use a bullet list. If this is a draft, finish it before the next write."
  } >&2
  exit 2
fi
exit 0
