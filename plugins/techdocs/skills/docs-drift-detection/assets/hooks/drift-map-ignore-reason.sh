#!/usr/bin/env bash
# Report a drift-map.yaml whose ignore entries lack a reason. Deterministic: standard tools only,
# no network, no secrets.
#
# What it checks: after a Write or Edit of a file named drift-map.yaml, it reads the whole file
# from disk (an Edit carries only a fragment) and reports, as file:line on stderr, every entry
# under the top-level `ignore:` key that has no non-empty `reason`. A reason counts when the
# value is any text, a block scalar with content, or text on the following indented lines; a
# missing key, an empty value, "", '' and null or ~ do not.
#
# Known limits: it reads YAML by line shape, not with a parser. It judges only a block
# sequence of entries under a column-zero `ignore:`; a flow list (`ignore: [..]`) or a flow
# mapping that spans lines is not judged, and neither is an `ignore:` nested under another key.
# A file over 1 MiB is refused rather than judged. A symlink is read through.
#
# PostToolUse feedback comes after the write: the file is already changed. Exit 2 only feeds
# the message back so the file can be fixed; it cannot undo the write.
set -Eeuo pipefail

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

case "$file" in
  drift-map.yaml | */drift-map.yaml) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the hook has work to do, so a missing scanner is a refusal, not a pass.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the ignore entries yourself." >&2
    exit 2
  fi
done

rc=0
size="$(LC_ALL=C wc -c <"$file")" || rc=$?
if [ "$rc" -ne 0 ]; then
  echo "blocked: could not read $file to check its ignore entries. Check the file is readable, then retry." >&2
  exit 2
fi
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not judge. Split the drift map, or check its ignore entries yourself." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; only the
# first two are an answer. A file with no ignore key has nothing to judge.
has=0
LC_ALL=C grep -Eq 'ignore[[:space:]]*:' -- "$file" || has=$?
if [ "$has" -gt 1 ]; then
  echo "blocked: could not read $file to check its ignore entries. Check the file is readable, then retry." >&2
  exit 2
fi
[ "$has" -eq 0 ] || exit 0

# One awk pass, linear in the file: every test is anchored at the start of a line or is a plain
# index() search, and nothing trims the end of a long line. It prints "@@done" last, so an awk
# that did not run (unreadable file, killed) is told from one that found nothing wrong.
#   state: inblock   inside the top-level ignore sequence
#          open      an entry has started and is not yet closed
#          has       the open entry has a reason
#          pending   a reason key was seen with no text yet; a deeper-indented line supplies it
awk_rc=0
verdict="$(
  LC_ALL=C HOOK_FILE="$file" awk '
    function indent(s) { match(s, /^[ \t]*/); return RLENGTH }
    function blank(s) { return s !~ /[^ \t]/ }
    function shown(s) { return length(s) > 200 ? substr(s, 1, 200) "..." : s }
    function close_entry() {
      if (open && !has) printf "%s:%d: ignore entry has no reason: %s\n", ENVIRON["HOOK_FILE"], start, shown(startline)
      open = 0; has = 0; pending = 0
    }
    # Judge the text after "reason:". Empty, "", '"'"''"'"' and null or ~ are no reason; a block
    # scalar header or nothing at all waits for an indented continuation line.
    function judge(val,    at) {
      at = index(val, " #"); if (at) val = substr(val, 1, at - 1)
      at = index(val, "\t#"); if (at) val = substr(val, 1, at - 1)
      sub(/^[ \t]+/, "", val)
      if (blank(val) || val ~ /^[|>][-+0-9]*[ \t]*$/) { pending = 1; return }
      if (val ~ /^(null|Null|NULL|~)[ \t]*$/) return
      if (val ~ /^("[ \t]*"|'"'"'[ \t]*'"'"')[ \t]*$/) return
      has = 1
    }
    function keyline(s,    body) {
      body = s
      sub(/^[ \t]+/, "", body)
      if (body ~ /^("reason"|'"'"'reason'"'"'|reason)[ \t]*:/) {
        sub(/^("reason"|'"'"'reason'"'"'|reason)[ \t]*:/, "", body)
        pending = 0
        judge(body)
      }
    }
    NR == 1 && index($0, "\357\273\277") == 1 { $0 = substr($0, 4) }
    {
      line = $0
      sub(/\r$/, "", line)
      if (!inblock) {
        if (line ~ /^ignore[ \t]*:/) {
          rest = line
          sub(/^ignore[ \t]*:/, "", rest)
          inblock = (blank(rest) || rest ~ /^[ \t]*#/)
          listind = -1
        }
        next
      }
      if (blank(line) || line ~ /^[ \t]*#/) next
      ind = indent(line)
      if (ind == 0 && line !~ /^-([ \t]|$)/) { close_entry(); inblock = 0; if (line ~ /^ignore[ \t]*:/) { rest = line; sub(/^ignore[ \t]*:/, "", rest); inblock = (blank(rest) || rest ~ /^[ \t]*#/); listind = -1 } ; next }
      dash = (line ~ /^[ \t]*-([ \t]|$)/)
      if (dash && (listind < 0 || ind <= listind)) {
        close_entry()
        listind = ind
        open = 1; start = NR; startline = line
        after = substr(line, ind + 2)
        sub(/^[ \t]+/, "", after)
        keyind = ind + 1 + (length(substr(line, ind + 2)) - length(after))
        if (blank(after) || after ~ /^#/) { keyind = -1; next }
        if (after ~ /^\{/) {
          if (after ~ /(^|[{,])[ \t]*("reason"|'"'"'reason'"'"'|reason)[ \t]*:[ \t]*[^ \t,}]/ && after !~ /reason"?'"'"'?[ \t]*:[ \t]*(""|'"'"''"'"'|null|~)[ \t]*[,}]/) has = 1
          next
        }
        keyline(after)
        next
      }
      if (!open) next
      if (keyind < 0) keyind = ind
      if (pending) {
        if (ind > keyind) { has = 1; pending = 0; next }
        pending = 0
      }
      if (ind == keyind) keyline(line)
    }
    END { close_entry(); print "@@done" }
  ' <"$file"
)" || awk_rc=$?
if [ "$awk_rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for ignore entries (awk status $awk_rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
missing="${verdict%@@done}"
missing="${missing%$'\n'}"

if [ -n "$missing" ]; then
  {
    echo "blocked (the write already happened; correct the file): every ignore entry in the drift map needs a non-empty reason, so the next person regenerating the map can tell a judgement from an omission:"
    printf '%s\n' "$missing"
  } >&2
  exit 2
fi
exit 0
