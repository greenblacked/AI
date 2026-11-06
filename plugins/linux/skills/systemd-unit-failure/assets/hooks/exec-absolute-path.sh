#!/usr/bin/env bash
# Report a written systemd unit whose Exec line starts a relative path that has a slash.
#
# What it checks: in a file named *.service or *.service.d/*.conf, every ExecStart=,
# ExecStartPre=, ExecStartPost=, ExecCondition=, ExecReload=, ExecStop= and ExecStopPost=
# line (and its backslash continuation) whose command, after the optional prefix characters
# (- @ : + !), has a first word that contains a slash but does not start with one. systemd
# refuses ./server and bin/run, the unit then fails with status 203/EXEC before the program
# runs, and the program's own log stays empty. A bare name such as "server" is valid (systemd
# resolves it on a fixed search path), a path starting with a % specifier is valid, and an
# empty value resets the list in a drop-in, so none of those is reported.
#
# The check reads the WRITTEN FILE from disk at tool_input.file_path, because an Edit carries
# only a fragment. It does not read the command text and parses no shell. Exit 2 puts file:line
# findings on stderr; exit 0 allows. A file over 1 MiB is refused unread.
#
# Known limits: PostToolUse runs after the write, so exit 2 only feeds the message back to the
# model, which can fix the file but cannot undo the write. A first word that is a $VARIABLE or
# sits inside quotes with a space is not judged. Specifiers other than a leading % are not
# expanded. A comment line that ends in a backslash is read as continuing the comment. Only the
# first word of the command is judged, not whether the file exists. Standard tools only, no
# network, no secrets.
set -Eeuo pipefail

input="$(cat)"
file=""
# Either parser prints nothing, and the hook allows, for input it cannot read a path from:
# invalid JSON, a non-object, a missing tool_input, or a path that is not a string.
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

# Only a unit file or a drop-in for one. Anything else, and no path at all, is not judged.
case "$file" in
  *.service | *.service.d/*.conf) ;;
  *) exit 0 ;;
esac
# A file that is not there (a deleted unit, a path from another machine) has nothing to judge.
[ -f "$file" ] || exit 0

# From here on the hook has something to judge, so a missing tool is a refusal and not a pass:
# letting the write through unchecked would make the hook look like it ran.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the Exec lines yourself." >&2
    exit 2
  fi
done
export LC_ALL=C

# No real unit is near 1 MiB. Refusing bounds the work and keeps the hook inside its timeout,
# because a hook that outlasts it fails open.
size="$(wc -c <"$file")" || size=""
case "$size" in
  '' | *[!0-9' ']*)
    echo "blocked: could not measure $file, so it was not judged. Retry; if it repeats, check the file's permissions." >&2
    exit 2
    ;;
esac
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not judge. Split the unit, or check its Exec lines yourself." >&2
  exit 2
fi

# Cheap screen: a unit with no Exec line has nothing to report. grep -c prints a count even
# for no match, so no count means grep did not run; only status 0 with a count or status 1
# with a count of 0 is an answer.
rc=0
count="$(grep -c -E '^[[:space:]]*Exec[A-Za-z]*[[:space:]]*=' <"$file")" || rc=$?
case "$rc:$count" in
  0:[1-9]*) ;;
  1:0) exit 0 ;;
  *)
    echo "blocked: could not scan $file with grep (status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
    exit 2
    ;;
esac

# One awk pass, linear in the file: every pattern is anchored at the start of a line or a word
# and no regex is run against the end of a long input. awk prints a last line, @@done, so an awk
# that did not run to the end (killed, or out of space) is told from one that found nothing.
# State across lines: `pending` means an Exec line was empty after its prefixes and ended in a
# backslash, so the command is the next line; `skip` means the current line continues a value
# or a comment that has already been judged.
rc=0
verdict="$(
  HOOK_FILE="$file" awk '
    function judge(cmd, lineno, full,    w, c, sp) {
      sp = match(cmd, /[ \t]/)
      w = sp ? substr(cmd, 1, sp - 1) : cmd
      c = substr(w, 1, 1)
      if (c == "\"" || c == "\047") {
        w = substr(w, 2)
        c = substr(w, 1, 1)
      }
      if (index(w, "/") && c != "/" && c != "%" && c != "$") {
        found++
        if (found <= 20) printf "%s:%d: %s\n", ENVIRON["HOOK_FILE"], lineno, substr(full, 1, 200)
      }
    }
    {
      line = $0
      n = length(line)
      if (substr(line, n, 1) == "\r") {
        line = substr(line, 1, n - 1)
        n--
      }
      bs = (substr(line, n, 1) == "\\")
      # The continuation backslash is not part of the value.
      text = bs ? substr(line, 1, n - 1) : line
      sub(/^[ \t]+/, "", text)
      if (pending) {
        cmd = text
        sub(/^[-@:+! \t]+/, "", cmd)
        if (cmd == "" && bs) next
        pending = 0
        if (cmd != "") judge(cmd, NR, line)
        skip = bs
        next
      }
      if (skip) {
        skip = bs
        next
      }
      first = substr(text, 1, 1)
      if (first == "#" || first == ";") {
        skip = bs
        next
      }
      if (match(text, /^Exec(Start|StartPre|StartPost|Condition|Reload|Stop|StopPost)[ \t]*=/)) {
        cmd = substr(text, RLENGTH + 1)
        sub(/^[-@:+! \t]+/, "", cmd)
        if (cmd == "") {
          pending = bs
          skip = 0
          next
        }
        judge(cmd, NR, line)
      }
      skip = bs
    }
    END { print "@@done" }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for relative Exec paths (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
found="${verdict%@@done}"
found="${found%$'\n'}"

if [ -n "$found" ]; then
  {
    echo "blocked: an Exec line starts a relative path. systemd requires an absolute path (or a bare name),"
    echo "so this unit will fail with status 203/EXEC before the program runs. Use the full path:"
    printf '%s\n' "$found"
  } >&2
  exit 2
fi
exit 0
