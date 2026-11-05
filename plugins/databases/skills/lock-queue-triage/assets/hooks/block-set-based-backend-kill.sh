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

# Neither parser present: degrade by allowing, because a hook that blocks everything on a
# missing tool is worse than no hook.
# Matched without regard to case, since SQL keywords and function names are not case-sensitive.
# A command that never names either function has nothing to judge; allow it at once, whatever
# its size. The text reaches grep as a here-string, not through a pipe: grep -q quits at its
# first match, and under pipefail a printf still writing into it would fail the pipeline.
if ! grep -qiE 'pg_(terminate|cancel)_backend' <<<"$command"; then
  exit 0
fi

# Trimming one huge argument with the parameter expansions below is slower than linear, so a
# large command could outlast the hook timeout, and a timed-out hook fails open. Refuse one
# that names a kill function and is too large to judge instead.
if [ "$(printf '%s' "$command" | wc -c)" -gt 32768 ]; then
  echo "blocked: the command calls pg_terminate_backend or pg_cancel_backend and is larger than 32 KiB, which this hook will not judge. Put the SQL in a short command with one literal pid you recorded from the blocking chain" >&2
  exit 2
fi

# Each match runs from the opening parenthesis to the first closing one, capped at 256 bytes so
# no single argument is trimmed at length. Anything that is not a digit string there (a column
# such as pid, a subquery, a bare word, or an argument too long to be a pid) could end every
# session the query returns, so it is refused.
while IFS= read -r call; do
  [ -n "$call" ] || continue
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
done < <(printf '%s\n' "$command" | grep -oiE 'pg_(terminate|cancel)_backend[[:space:]]*\([^)]{0,256}' || true)
exit 0
