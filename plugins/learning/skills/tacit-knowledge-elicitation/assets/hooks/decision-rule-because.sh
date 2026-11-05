#!/usr/bin/env bash
# Report each decision rule in a written interview file that gives no reason. A rule is a line
# starting "If " (after any quote, bullet or number marker); it needs the word "because" on that
# line or on the lines that continue it, up to the next blank line, heading, bullet or rule.
# Acts on a .md file under an interviews/ directory, or any .md file whose name contains
# decision-rule. Deterministic: standard tools only, no network, no secrets, nothing is run from
# the file.
#
# It reads the WRITTEN FILE from disk at tool_input.file_path, because an Edit carries only a
# fragment. Known limits:
#   - It runs on PostToolUse, so the write has already happened; exit 2 feeds the findings back to
#     the model to fix, it cannot undo the write.
#   - A raw transcript under interviews/ also holds sentences that begin "If " without being rules;
#     those are reported too. Keep transcripts outside interviews/ or install the hook for the rule
#     sheets only.
#   - Only a capitalised "If" starts a rule; "if", "**If**" and a table cell are not read. The word
#     "because" is matched in any case, but "since" or "as" are not accepted as a reason.
#   - A file over 1 MiB is refused unread rather than scanned.
set -Eeuo pipefail
export LC_ALL=C

input="$(cat)"
file=""
# Either parser prints nothing, and the hook allows, for input it cannot read a path from.
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

# Neither parser present, or no path: allow, because a hook that blocks everything on a missing
# tool is worse than no hook.
[ -n "$file" ] || exit 0

case "$file" in
  interviews/*.md | */interviews/*.md) ;;
  *)
    case "${file##*/}" in
      *decision-rule*.md) ;;
      *) exit 0 ;;
    esac
    ;;
esac
[ -f "$file" ] || exit 0

# From here the hook judges a file, so a missing tool must not let it through unjudged.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the rules in it by hand." >&2
    exit 2
  fi
done

rc=0
size="$(wc -c <"$file")" || rc=$?
if [ "$rc" -ne 0 ]; then
  echo "blocked: could not read $file to check its decision rules. Check the file is readable, then retry." >&2
  exit 2
fi
size="${size//[!0-9]/}"
if [ "${size:-0}" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan for decision rules. Split the interview notes into smaller files and keep the rules in a decision-rule sheet." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; only the
# first two are an answer. A file with no rule line needs no awk pass.
rc=0
grep -q -E '^[[:space:]>]*([-*+]|[0-9]+[.)])?[[:space:]]*If[[:space:]]' <"$file" || rc=$?
if [ "$rc" -eq 1 ]; then
  exit 0
elif [ "$rc" -ne 0 ]; then
  echo "blocked: could not scan $file for decision rules (grep status $rc), so it was not judged. Check the file is readable, then retry." >&2
  exit 2
fi

# One awk pass, linear in the file. The pending rule is flushed at a blank line, a heading, a
# bullet, a new rule or the end of the file. Every pattern is anchored at the start of the line
# and nothing is anchored at its end. awk prints a last line, @@done, so an awk that did not
# run to the end is told from one that found nothing wrong. Only the first 20 findings print.
rc=0
verdict="$(
  HOOK_FILE="$file" awk '
    function flush() {
      if (pend && !ok) {
        n++
        if (n <= 20) printf "%s:%d: %s\n", ENVIRON["HOOK_FILE"], start, substr(text, 1, 200)
      }
      pend = 0
    }
    {
      line = $0
      probe = line
      sub(/^[ \t\r]+/, "", probe)
      if (probe == "") { flush(); next }
      if (match(line, /^[ \t>]*([-*+]|[0-9]+[.)])?[ \t]*If[ \t]/)) {
        flush()
        pend = 1; start = NR; text = line; ok = index(tolower(line), "because") > 0
        next
      }
      if (match(line, /^[ \t>]*([-*+]|[0-9]+[.)])[ \t]/) || substr(probe, 1, 1) == "#") { flush(); next }
      if (pend && !ok && index(tolower(line), "because")) ok = 1
    }
    END {
      flush()
      if (n > 20) printf "... and %d more\n", n - 20
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for decision rules (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
missing="${verdict%@@done}"
missing="${missing%$'\n'}"

if [ -n "$missing" ]; then
  {
    echo "blocked: these decision rules give no reason. The write already happened; add 'because ...' to each rule,"
    echo "on the same line or the lines that continue it, naming why the first action is the right one:"
    printf '%s\n' "$missing"
  } >&2
  exit 2
fi
exit 0
