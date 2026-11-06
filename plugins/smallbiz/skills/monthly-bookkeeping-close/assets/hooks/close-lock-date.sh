#!/usr/bin/env bash
# Require a calendar date on every "Period locked: yes" line of a month-close note.
#
# Checks: for a written file whose basename contains "close" and ends .md, any line that says
# "Period locked:" followed by yes or true must carry a calendar date on the same line
# (2026-10-03, 3/10/2026, 2026/10/3, "3 Oct 2026" or "Oct 3, 2026"). A lock with no date
# cannot be checked against the books later. The file is read from disk at tool_input.file_path,
# because an Edit carries only a fragment.
# Deterministic: standard tools only, no network, no secrets.
#
# Known limits: only the line itself is read, so a date on the next line does not count; a
# digit string such as 12026-10-031 passes as a date; a bracketed placeholder such as
# "[yes, YYYY-MM-DD]" is not a lock claim and is ignored; a file over 1 MiB is refused, not
# judged. This hook runs on PostToolUse, so the write has already happened: exit 2 feeds the
# findings back to the model to correct the file and cannot undo the write.
set -Eeuo pipefail
export LC_ALL=C

input="$(cat)"
file=""
# Either parser prints nothing for input it cannot read a path from; the hook then allows.
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

# Neither parser present, or no path: allow, because a hook that blocks on a missing
# tool is worse than none.
[ -n "$file" ] || exit 0

base="${file##*/}"
lower="$(printf '%s' "$base" | tr 'A-Z' 'a-z')"
case "$lower" in
  *close*.md) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here a file is to be judged, so a missing scanner must not let it through.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the lock line yourself." >&2
    exit 2
  fi
done

size=0
size="$(wc -c <"$file")" || size=-1
if [ "$size" -lt 0 ] 2>/dev/null || [ -z "$size" ]; then
  echo "blocked: could not read $file to check its lock line. Check the file is readable, then retry." >&2
  exit 2
fi
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not judge. Keep the month-close note small, or check its lock line yourself." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; only the
# first two are an answer. The pre-filter spares awk the work on a note with no lock line.
found=0
grep -qaiF 'period locked' <"$file" || found=$?
if [ "$found" -gt 1 ]; then
  echo "blocked: could not read $file to check its lock line. Check the file is readable, then retry." >&2
  exit 2
fi
[ "$found" -eq 0 ] || exit 0

# One linear awk pass. Every repetition is bounded or anchored to a fixed prefix, so no run of
# input is rescanned from many start positions. The last line, @@done, tells an awk that found
# nothing from one that did not run.
rc=0
verdict="$(
  HOOK_FILE="$file" awk '
    function dated(s) {
      return s ~ /[0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?/ \
        || s ~ /[0-9][0-9]?\/[0-9][0-9]?\/[0-9][0-9][0-9][0-9]/ \
        || s ~ /[0-9][0-9][0-9][0-9]\/[0-9][0-9]?\/[0-9][0-9]?/ \
        || s ~ /[0-9][0-9]?(st|nd|rd|th)? (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]?[a-z]?[a-z]?[a-z]?[a-z]?[a-z]?,? [0-9][0-9][0-9][0-9]/ \
        || s ~ /(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]?[a-z]?[a-z]?[a-z]?[a-z]?[a-z]?\.? [0-9][0-9]?(st|nd|rd|th)?,? [0-9][0-9][0-9][0-9]/
    }
    {
      low = tolower($0)
      at = index(low, "period locked")
      if (!at) next
      rest = substr(low, at + 13, 400)
      if (rest !~ /^[*_ \t]*:[*_ \t]*(yes|true)([ \t,.;)(*_-]|$)/) next
      if (!dated(low)) printf "%s:%d: %s\n", ENVIRON["HOOK_FILE"], NR, substr($0, 1, 200)
    }
    END { print "@@done" }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for its lock line (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
missing="${verdict%@@done}"
missing="${missing%$'\n'}"

if [ -n "$missing" ]; then
  {
    echo "blocked (the write already happened; correct the file): a month cannot be recorded as locked without the date the lock was set. Put the date on the same line, for example 'Period locked: yes, 2026-10-03':"
    printf '%s\n' "$missing"
  } >&2
  exit 2
fi
exit 0
