#!/usr/bin/env bash
# Refuse pg_terminate_backend or pg_cancel_backend with a non-literal pid. Deterministic: standard tools only, no network, no secrets.
# It reads the command text and nothing else. It undoes shell quoting, backslashes and line
# continuations before matching, and refuses a command that names a backend kill in a spelling it
# cannot read ($'..' escapes, brace expansion, a variable or substitution as the command, which is read right after a separator or after
# sudo, exec, command and similar wrappers, not after other wrappers) rather
# than guessing. A script file or .sql file the command runs is out of scope: the hook cannot see
# what is in it.
set -Eeuo pipefail

input="$(cat)"
command=""
# Either parser prints nothing, and the hook allows, for input it cannot read a command from:
# invalid JSON, JSON that is not an object, a missing or non-object `tool_input`, or a null
# `command`. A `false` command is kept by both parsers, so they agree. Erroring out
# instead would report a failure over a payload it never needed.
if command -v jq >/dev/null 2>&1; then
  command="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.command | if . == null then empty elif type=="string" then . else tojson end) else empty end' \
    2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  command="$(printf '%s' "$input" | python3 -I -c \
    'import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
value = tool.get("command") if isinstance(tool, dict) else None
if value is None:
    value = ""
# jq -r prints a string as is and anything else as JSON; this follows it, so both branches
# reach the same verdict (the whitespace inside a printed list can differ).
print(value if isinstance(value, str) else json.dumps(value))' || true)"
fi

# hits TEXT GREP-OPTION...: succeeds when grep finds a match in TEXT, fails when it finds none, and
# refuses the command on any other outcome. TEXT reaches grep as a here-string, not through a pipe:
# grep quits early under -q, and a writer piped into it would then die of SIGPIPE, which pipefail
# turns into a failed pipeline that reads as "no match". Bash writes a large here-string to a
# temporary file; when that write fails (a full disk, a file-size limit) the redirection fails with
# status 1 and grep never runs, which `if grep ...` would also read as "no match" and allow.
# grep -c prints a count even for no match, so no count means grep did not run. Only status 0 with
# a count or status 1 with a count of 0 is an answer. Standalone like every hook here, so this
# function is copied rather than sourced.
hits() {
  local text=$1 count rc=0
  shift
  count="$(grep -c "$@" <<<"$text")" || rc=$?
  case "$rc:$count" in
    0:[1-9]*) return 0 ;;
    1:0) return 1 ;;
  esac
  echo "blocked: could not scan the text with grep (status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
}

# Neither parser present: degrade by allowing, because a hook that blocks everything on a
# missing tool is worse than no hook.
[ -n "$command" ] || exit 0
# Byte-wise matching (LC_ALL=C): under a UTF-8 locale GNU grep takes quadratic time on the patterns
# below for a long run of one kind of character, and a timed-out hook fails open. A name and a
# keyword are ASCII, and upper case is only folded for ASCII.
export LC_ALL=C
# Matched without regard to case, since SQL keywords and function names are not case-sensitive.
#
# The command is a shell line carrying SQL, so the shell can split the function name where a text
# match cannot see it: psql -c 'select pg_terminate_back'"end(pid)" reaches psql as
# pg_terminate_backend(pid). So the command is normalised first: a backslash-newline continuation
# is joined, the $ of $'..' and $".." is dropped, and quotes and backslashes are deleted. The
# judgement below runs on the command as written and on the normalised one, because a quoted pid
# ('123') is a non-literal pid to this hook as written. What cannot be normalised is refused
# instead, when the command also names a kill function or a fragment of one: a $'..' string with
# a backslash (hex and octal escapes), a brace expansion with a comma or `..` outside quotes, and
# a variable, a command substitution or a backtick where the command word goes (right after a separator, a group opener, then, do or else, or one of the wrappers sudo, command, exec, xargs, nohup, time, busybox and builtin, with any NAME=value assignments between; a command run through another wrapper is not read) (c=psql; $c -c ...).
# A variable that is only the start of a path ($HOME/bin/psql) is read as the path it ends in.
# A script file the command runs is out of scope: this hook sees only the command text.
# Standalone like every hook here, so these two functions are copied rather than sourced.
# A line continues only when it ends in an odd number of backslashes: `\\` is an escaped backslash and the
# command ends there. The run is counted from the end, so a long run costs time in its own length only.
# A line that would join and has a # at the start of a word (after the line start, a space or a shell
# operator, quoted or not) is uncertain: bash does not join a comment line and does join a quoted
# # such as 'a # b', and the hook does not track quotes. For such a command the output holds both
# readings, one after the other, joined and then unjoined, so a rule that refuses either one
# refuses the command. Lines without such a # keep the single joined reading.
normalise() {
  LC_ALL=C awk '{ n = length($0); k = 0; while (k < n && substr($0, n - k, 1) == "\\") k++; if (k % 2) { body = substr($0, 1, n - 1); printf "%s", body; cont = 1; if ($0 ~ /(^|[ \t\r;&|()<>`])#/) { unc = 1; b[++m] = body "\n" } else b[++m] = body; next } print; b[++m] = $0 "\n"; cont = 0 } END { if (cont) { print ""; b[++m] = "\n" } if (unc) for (i = 1; i <= m; i++) printf "%s", b[i] }' |
    sed -E "s/[\$][\"']//g" | tr -d "\"'\\\\"
}
# unreadable ORIGINAL PLAIN: succeeds when the command uses a spelling that normalise cannot read.
unreadable() {
  local outside cmdpos
  if hits "$1" -E "[\$]'[^']*[\\\\]"; then return 0; fi
  outside="$(printf '%s' "$1" | sed -E "s/'[^']*'|\"[^\"]*\"//g")"
  if hits "$outside" -E '(^|[^$])\{[^{}[:space:]]*(,|\.\.)[^{}[:space:]]*\}'; then return 0; fi
  cmdpos='(^|[;&|`]|[$][(]|[[:space:]](then|do|else))[[:space:]]*([({][[:space:]]*)*((sudo|command|exec|xargs|nohup|time|busybox|builtin|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*)[[:space:]]+)*([$][A-Za-z_][A-Za-z0-9_]*([^/A-Za-z0-9_]|$)|[$]\{[^}]*\}([^/]|$)|[$][(0-9@*]|`)'
  hits "$(printf '%s' "$2" | tr '\n\r' ';;')" -E "$cmdpos"
}
# normalise needs awk. Without it the pipeline below fails with status 127, which is not a block,
# so the command would run unjudged; refuse instead, because a missing tool is not a reason to allow.
if [ -n "$command" ] && ! command -v awk >/dev/null 2>&1; then
  echo "blocked: awk is not installed, so this hook cannot read the command and did not judge it. Install awk (any POSIX awk), or run the command yourself." >&2
  exit 2
fi
plain="$(printf '%s\n' "$command" | normalise)"
plain_flat="$(printf '%s' "$plain" | tr '\n\r' '  ')"

# A command that never names either function has nothing to judge; allow it at once, whatever
# its size, unless it is small enough to look at and uses a spelling that could hide the name.
named=0
if hits "$command" -iE 'pg_(terminate|cancel)_backend' || hits "$plain_flat" -iE 'pg_(terminate|cancel)_backend'; then
  named=1
elif [ "$(printf '%s' "$command" | wc -c)" -le 32768 ] &&
  hits "$plain_flat" -iE 'terminate|cancel_backend|_backend'; then
  named=2
else
  exit 0
fi

# Trimming one huge argument with the parameter expansions below is slower than linear, so a
# large command could outlast the hook timeout, and a timed-out hook fails open. Refuse one
# that names a kill function and is too large to judge instead.
if [ "$named" -eq 1 ] && [ "$(printf '%s' "$command" | wc -c)" -gt 32768 ]; then
  echo "blocked: the command calls pg_terminate_backend or pg_cancel_backend and is larger than 32 KiB, which this hook will not judge. Put the SQL in a short command with one literal pid you recorded from the blocking chain" >&2
  exit 2
fi

if unreadable "$command" "$plain"; then
  echo "blocked: this hook could not read the command (a \$'...' escape, a brace expansion, or a variable or substitution where the command goes) and it names a backend kill. Write the SQL plainly, with pg_terminate_backend(<pid>) and one literal pid you recorded from the blocking chain." >&2
  exit 2
fi
[ "$named" -eq 1 ] || exit 0

# judge TEXT: refuses the command (exit 2) when TEXT calls a kill function with anything but a
# literal pid.
judge() {
  # Newlines and carriage returns become spaces and double quotes are deleted before the scan, so
  # a call split across lines (pg_terminate_backend, a newline, then (pid)) and a quoted
  # identifier ("pg_terminate_backend"(pid)) are one call to the pattern below, as SQL reads them.
  # Each match runs from the function name to the opening parenthesis and on to the first closing
  # parenthesis, capped at 256 bytes so no single argument is trimmed at length. Only whitespace
  # may sit between the name and its parenthesis: a comment (name/**/(pid)) or any other text there
  # is a call this hook cannot read, so it is refused like a column or subquery. Anything that is
  # not a digit string in the parentheses (a column such as pid, a subquery, a bare word, or an
  # argument too long to be a pid) could end every session the query returns, so it is refused.
  local flat calls rc=0 call gap arg
  flat="$(printf '%s' "$1" | tr -d '"' | tr '\n\r' '  ')"
  calls="$(printf '%s\n' "$flat" | grep -oiE 'pg_(terminate|cancel)_backend[^(]*\([^)]{0,256}'; exit "${PIPESTATUS[1]}")" || rc=$?
  case "$rc" in
    0 | 1) ;;
    *)
      echo "blocked: could not scan the command for pg_terminate_backend calls (grep status $rc), so it was not judged. Retry the command." >&2
      exit 2
      ;;
  esac
  # $calls is bounded: the command is at most 32 KiB here (the cap above), and grep -o cannot print
  # more than it read. Bash 5.1 and later write a here-string that fits the pipe capacity (64 KiB
  # on Linux) through a pipe and not a temporary file, so the read below cannot meet the failed
  # temporary-file write that hits() guards against. On an older bash the redirection can fail,
  # and set -e then ends the hook with status 1, which is not a block.
  while IFS= read -r call; do
    [ -n "$call" ] || continue
    gap="${call%%\(*}"
    gap="${gap#*[bB][aA][cC][kK][eE][nN][dD]}"
    if [ -n "${gap//[[:space:]]/}" ]; then
      echo "blocked: something other than whitespace sits between the function name and its parenthesis; write pg_terminate_backend(<pid>) with one literal pid you recorded from the blocking chain" >&2
      exit 2
    fi
    arg="${call#*(}"
    # A span that hit the cap may go on to something other than digits (111...1+pid), and the
    # cut-off part cannot be judged, so it is refused.
    if [ "${#arg}" -ge 256 ]; then
      echo "blocked: the argument is too long to be a pid; pass one literal pid you recorded from the blocking chain" >&2
      exit 2
    fi
    # pg_terminate_backend(pid, timeout) takes a literal timeout as its second argument; only
    # the pid is judged, and a comma inside a subquery still leaves a non-digit first part.
    arg="${arg%%,*}"
    arg="${arg#"${arg%%[![:space:]]*}"}"
    arg="${arg%"${arg##*[![:space:]]}"}"
    case "$arg" in
      '' | *[!0-9]*)
        echo "blocked: pass one literal pid you recorded from the blocking chain, not a column or subquery" >&2
        exit 2
        ;;
    esac
  done <<<"$calls"
}
judge "$command"
[ "$plain_flat" = "$command" ] || judge "$plain_flat"
exit 0
