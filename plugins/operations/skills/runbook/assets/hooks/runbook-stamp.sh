#!/usr/bin/env bash
# Report a written runbook whose top lines carry no usable owner or last-verified date. A
# runbook with no owner has nobody to update it, and one with no date cannot be told from a
# document that was proven last month. Deterministic: standard tools only, no network, no
# secrets, nothing run from the file.
#
# What it checks. For a written .md file under a runbooks/ directory, or whose name contains
# "runbook", the file is read from disk at tool_input.file_path, so an Edit is judged on the
# whole file and not on its fragment. In the first 40 lines, outside code fences, it needs:
#   - an "Owner:" label with a value that is not empty and does not start with "[", which is
#     the unfilled template placeholder;
#   - a "Last verified:" label whose value starts with a real YYYY-MM-DD date;
#   - that date no later than tomorrow in UTC (one day of slack for a writer ahead of UTC).
# A label counts at the start of a line (after "-", ">" or blanks), or after "·", "|" or ";" on
# a line that holds both, such as "**Owner:** a · **Last verified:** 2026-01-02". Asterisks
# are ignored, so "**Owner:**", "**Owner**:" and "Owner:" all read the same, and label case
# does not matter. A finding prints file:line and a fixed message, never text from the file,
# and the hook exits 2. README.md, index.md and _index.md are skipped: they list runbooks.
# So is a verification record, which is evidence about a runbook and not one: a file whose name
# contains "verification-record", or whose first heading is "# Runbook verification record"
# (case and runs of spaces or tabs do not matter).
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the
#     model, which can fix the file; the hook cannot undo anything.
#   - Only a label near the top is read. A table row, an underscore or backtick label, or a
#     stamp further down is not seen. A heading that merely contains a label word is not one.
#   - The date is checked for shape and range (month 01-12, day 01-31), not against the
#     calendar, and not for whether anyone really verified anything. The future check needs a
#     bash with printf %(...)T (4.2 or later); on an older bash it is skipped, not failed.
#   - Only the file on disk after the write is judged, never a shell command that creates
#     one, so a runbook written by a heredoc is not seen. A file over 1 MiB is refused.
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

# A Markdown file in a runbooks/ directory at any depth, or whose own name has "runbook" in
# it. The directory name must match whole, so myrunbooks/ stays out; the file name is a
# substring match on purpose, because teams write runbook-db.md and db-runbook.md.
base="${file##*/}"
case "$base" in
  README.md | readme.md | index.md | _index.md) exit 0 ;;
  *[Vv]erification-record*) exit 0 ;;
esac
case "$file" in
  */[Rr]unbooks/*.md | [Rr]unbooks/*.md) ;;
  *)
    case "$base" in
      *[Rr]unbook*.md) ;;
      *) exit 0 ;;
    esac
    ;;
esac
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the owner and last-verified lines yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to check it for an owner and a last-verified date. Check the file is readable, then retry." >&2
  exit 2
fi
# No real runbook is near this size. The scan below is linear, so the limit bounds the work;
# a hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. A runbook is far smaller; check what was written to it." >&2
  exit 2
fi

# The latest date a stamp may carry: tomorrow in UTC. The builtin printf needs no external
# date; on a bash without %(...)T the limit stays empty and the future check is skipped.
limit=""
now="$(TZ=UTC0 printf '%(%s)T' -1 2>/dev/null)" || now=""
case "$now" in
  '' | *[!0-9]*) ;;
  *) limit="$(TZ=UTC0 printf '%(%Y-%m-%d)T' "$((now + 86400))" 2>/dev/null)" || limit="" ;;
esac
case "$limit" in
  [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
  *) limit="" ;;
esac

# One awk pass over at most 40 lines, each cut to 300 bytes first so no pattern ever sees a
# long line. The regexes are anchored or single-class, so each is linear. A code fence hides
# the stamp inside it, which is how a template shows one. awk prints a last line, @@done, so
# that an awk that did not run (killed, or the redirection failed) is told from one that
# found nothing wrong. A record found by its first heading prints only that last line. A finding is "line:message"; no text from the file is repeated.
rc=0
verdict="$(
  awk -v lim="$limit" '
    function label(l, name,    p, pre, t, n) {
      p = index(l, name ":")
      if (p == 0) return 0
      pre = substr(l, 1, p - 1)
      t = pre
      sub(/[ \t]+$/, "", t)
      if (t ~ /^[ \t>-]*$/) return p
      n = length(t)
      if (substr(t, n, 1) == "|" || substr(t, n, 1) == ";") return p
      if (n >= 2 && substr(t, n - 1, 2) == "\302\267") return p
      return 0
    }
    NR > 40 { exit }
    {
      raw = substr($0, 1, 300)
      gsub(/\r/, "", raw)
      s = raw
      sub(/^[ \t]+/, "", s)
      c = substr(s, 1, 3)
      if (c == "```" || c == "~~~") {
        if (!infence) { infence = 1; fence = c } else if (c == fence) infence = 0
        next
      }
      if (infence) next
      if (!headseen && s ~ /^#[ \t]/) {
        headseen = 1
        h = tolower(s)
        gsub(/[ \t]+/, " ", h)
        sub(/ $/, "", h)
        if (h == "# runbook verification record") record = 1
      }
      gsub(/\*/, "", raw)
      low = tolower(raw)
      if (!ownerline) {
        p = label(low, "owner")
        if (p) {
          ownerline = NR
          v = substr(raw, p + 6)
          sub(/^[ \t]+/, "", v)
          if (v == "" || substr(v, 1, 1) == "[") ownerbad = 1
        }
      }
      if (!dateline) {
        p = label(low, "last verified")
        if (p) {
          dateline = NR
          v = substr(raw, p + 14)
          sub(/^[ \t]+/, "", v)
          if (v !~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/ || substr(v, 11, 1) ~ /[0-9]/) {
            datebad = 1
          } else {
            m = substr(v, 6, 2) + 0
            d = substr(v, 9, 2) + 0
            if (m < 1 || m > 12 || d < 1 || d > 31) datebad = 1
            else if (lim != "" && substr(v, 1, 10) > lim) datefuture = 1
          }
        }
      }
    }
    END {
      if (record) { print "@@done"; exit }
      if (!ownerline) print "1:no Owner line in the first 40 lines. Add Owner: with a team or rota."
      else if (ownerbad) print ownerline ":Owner has no value or still holds the template placeholder. Name the team or rota."
      if (!dateline) print "1:no Last verified line in the first 40 lines. Add Last verified: YYYY-MM-DD, who and how."
      else if (datebad) print dateline ":Last verified has no valid YYYY-MM-DD date at its start. Write the date the steps were last run."
      else if (datefuture) print dateline ":Last verified is a date in the future. Write the date the steps were actually run."
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for an owner and a last-verified date (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
finding="${verdict%@@done}"
finding="${finding%$'\n'}"

if [ -n "$finding" ]; then
  {
    echo "blocked: $file does not carry a usable owner and last-verified stamp, so a reader cannot tell who maintains it or whether it was ever proven. The write already happened; fix the lines below."
    printf '%s\n' "$finding" | while IFS= read -r line; do
      printf '%s:%s\n' "$file" "$line"
    done
    echo "A stamp reads like: Owner: platform-oncall, then Last verified: 2026-03-14 by oncall during a game day. Do not move the date for an edit; record a check in runbook-verification-record.md."
  } >&2
  exit 2
fi
exit 0
