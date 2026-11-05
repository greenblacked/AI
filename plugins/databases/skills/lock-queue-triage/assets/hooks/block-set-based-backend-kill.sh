#!/usr/bin/env bash
# Refuse pg_terminate_backend or pg_cancel_backend with a non-literal pid. Deterministic: standard tools only, no network, no secrets.
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
# Matched without regard to case, since SQL keywords and function names are not case-sensitive.
# A command that never names either function has nothing to judge; allow it at once, whatever
# its size.
if ! hits "$command" -iE 'pg_(terminate|cancel)_backend'; then
  exit 0
fi

# Trimming one huge argument with the parameter expansions below is slower than linear, so a
# large command could outlast the hook timeout, and a timed-out hook fails open. Refuse one
# that names a kill function and is too large to judge instead.
if [ "$(printf '%s' "$command" | wc -c)" -gt 32768 ]; then
  echo "blocked: the command calls pg_terminate_backend or pg_cancel_backend and is larger than 32 KiB, which this hook will not judge. Put the SQL in a short command with one literal pid you recorded from the blocking chain" >&2
  exit 2
fi

# Newlines and carriage returns become spaces and double quotes are deleted before the scan, so
# a call split across lines (pg_terminate_backend, a newline, then (pid)) and a quoted
# identifier ("pg_terminate_backend"(pid)) are one call to the pattern below, as SQL reads them.
# Each match runs from the function name to the opening parenthesis and on to the first closing
# parenthesis, capped at 256 bytes so no single argument is trimmed at length. Only whitespace
# may sit between the name and its parenthesis: a comment (name/**/(pid)) or any other text there
# is a call this hook cannot read, so it is refused like a column or subquery. Anything that is
# not a digit string in the parentheses (a column such as pid, a subquery, a bare word, or an
# argument too long to be a pid) could end every session the query returns, so it is refused.
flat="$(printf '%s' "$command" | tr -d '"' | tr '\n\r' '  ')"
rc=0
calls="$(printf '%s\n' "$flat" | grep -oiE 'pg_(terminate|cancel)_backend[^(]*\([^)]{0,256}'; exit "${PIPESTATUS[1]}")" || rc=$?
case "$rc" in
  0 | 1) ;;
  *)
    echo "blocked: could not scan the command for pg_terminate_backend calls (grep status $rc), so it was not judged. Retry the command." >&2
    exit 2
    ;;
esac
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
exit 0
