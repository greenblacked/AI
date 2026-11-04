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
  # jq reads a leading BOM as a syntax error, but the engines and Python load such a file,
  # so strip it here rather than report a file that works.
  bom="$(printf '\357\273\277')"
  err="$(LC_ALL=C sed "1s/^${bom}//" "$file" | jq empty 2>&1)" || {
    echo "invalid JSON in $file: $err" >&2
    exit 2
  }
fi
exit 0
