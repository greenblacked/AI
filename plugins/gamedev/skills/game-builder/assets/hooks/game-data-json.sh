#!/usr/bin/env bash
# Report a written .json file under a data directory that does not parse. It only parses the
# file as data and never runs anything from it. Standard tools only, no network, no secrets.
set -Eeuo pipefail

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

case "$file" in
  */data/*.json | */Data/*.json | data/*.json | Data/*.json) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# Neither parser present: degrade by allowing, because a hook that blocks everything on a
# missing tool is worse than no hook.
if command -v python3 >/dev/null 2>&1; then
  err="$(python3 -I -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8-sig"))' "$file" 2>&1)" || {
    echo "invalid JSON in $file: ${err##*$'\n'}" >&2
    exit 2
  }
elif command -v jq >/dev/null 2>&1; then
  # jq reads a leading BOM as a syntax error, but the engines and Python load such a file, so
  # skip exactly one. The path is only ever a redirection target, never an argument, so a name
  # starting with a dash cannot be read as an option. `input | empty` fails on a file with no
  # value in it, which is what Python does, where `jq empty` would call it valid; so an empty
  # file, a BOM-only file and a file with two BOMs are all reported on both paths.
  bom="$(printf '\357\273\277')"
  # A NUL in the first bytes makes bash warn on stderr; the warning is noise here.
  { head3="$(LC_ALL=C head -c 3 < "$file" || true)"; } 2>/dev/null
  if [ "$head3" = "$bom" ]; then
    # jq 1.7 drops a BOM of its own, so a second one has to be caught here to match Python.
    { next3="$(tail -c +4 < "$file" | LC_ALL=C head -c 3 || true)"; } 2>/dev/null
    if [ "$next3" = "$bom" ]; then
      echo "invalid JSON in $file: more than one byte order mark" >&2
      exit 2
    fi
    err="$(tail -c +4 < "$file" | jq -n 'input | empty' 2>&1)" || {
      echo "invalid JSON in $file: $err" >&2
      exit 2
    }
  else
    err="$(jq -n 'input | empty' < "$file" 2>&1)" || {
      echo "invalid JSON in $file: $err" >&2
      exit 2
    }
  fi
fi
exit 0
