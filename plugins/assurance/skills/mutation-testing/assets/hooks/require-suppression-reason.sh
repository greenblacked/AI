#!/usr/bin/env bash
# Refuse a mutation-testing suppression written without a reason. Deterministic: standard
# tools only, no network, no secrets.
set -Eeuo pipefail

input="$(cat)"
text=""
# Either parser prints nothing, and the hook allows, for input it cannot read text from:
# invalid JSON, a non-object, a missing tool_input, or neither content nor new_string.
if command -v jq >/dev/null 2>&1; then
  text="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.content // .tool_input.new_string | if . == null then empty elif type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  text="$(printf '%s' "$input" | python3 -c \
    'import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
value = None
if isinstance(tool, dict):
    value = tool.get("content")
    if value is None:
        value = tool.get("new_string")
print(value if isinstance(value, str) else "")' || true)"
fi

# Neither parser present, or nothing to judge: allow, because a hook that blocks everything
# on a missing tool is worse than no hook.
[ -n "$text" ] || exit 0

# Judged on the written text alone, so for an Edit the reason must be in the same edit.
# A reason is words in a comment on the same line or the line directly above, or text after
# the colon on a Stryker line.
missing=""
prev=""
n=0
while IFS= read -r line || [ -n "$line" ]; do
  n=$((n + 1))
  case "$line" in
    *"Stryker disable"*)
      rest="${line#*Stryker disable}"
      case "$rest" in
        *:*) reason="${rest#*:}" ;;
        *) reason="" ;;
      esac
      if ! printf '%s' "$reason" | grep -Eq '[[:alnum:]]'; then
        missing="${missing}line ${n}: ${line}"$'\n'
      fi
      ;;
    *"pragma: no mutate"* | *"mutants::skip"* | *"infection-ignore"*)
      marker="$line"
      for m in "pragma: no mutate" "mutants::skip" "infection-ignore"; do
        marker="${marker//"$m"/}"
      done
      # Words after the marker on the same line (outside the marker itself), or a comment
      # line above carrying words.
      same="$(printf '%s' "$marker" | sed -E 's/^[[:space:]#/*-]+//' | grep -Eo '[[:alpha:]]{2,}' | head -n 1 || true)"
      above=""
      case "$prev" in
        *"#"* | *"//"* | *"/*"* | *"*"*)
          above="$(printf '%s' "$prev" | grep -Eo '[[:alpha:]]{2,}' | head -n 1 || true)"
          ;;
      esac
      if [ -z "$same" ] && [ -z "$above" ]; then
        missing="${missing}line ${n}: ${line}"$'\n'
      fi
      ;;
  esac
  prev="$line"
done <<<"$text"

if [ -n "$missing" ]; then
  {
    echo "blocked: a mutation suppression needs a reason. Say why the mutant is equivalent or accepted,"
    echo "on the same line or in a comment directly above, within this same write or edit:"
    printf '%s' "$missing"
  } >&2
  exit 2
fi
exit 0
