#!/usr/bin/env bash
# Refuse a timestamp or git SHA written into a generated or build-info file.
# Deterministic: standard tools only, no network, no secrets.
set -Eeuo pipefail

input="$(cat)"
path=""
content=""
# Either parser prints nothing, and the hook allows, for input it cannot read: invalid JSON,
# a non-object payload, or a missing or non-object `tool_input`. Content is `content` for
# Write and `new_string` for Edit.
if command -v jq >/dev/null 2>&1; then
  path="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.file_path | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
  content="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then ((.tool_input.content // .tool_input.new_string) | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  path="$(printf '%s' "$input" | python3 -I -c \
    'import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
value = tool.get("file_path") if isinstance(tool, dict) else None
print(value if isinstance(value, str) else "")' || true)"
  content="$(printf '%s' "$input" | python3 -I -c \
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

# Neither parser present, or nothing to inspect: allow, because a hook that blocks
# everything on a missing tool is worse than no hook.
if [ -z "$path" ] || [ -z "$content" ]; then
  exit 0
fi

base="${path##*/}"
generated=0
case "$path" in
  */generated/* | */gen/*) generated=1 ;;
esac
case "$base" in
  version.* | build-info* | *.generated.*) generated=1 ;;
esac
[ "$generated" -eq 1 ] || exit 0

# The content reaches grep as a here-string, not through a pipe: grep -q quits at its first
# match, and under pipefail a printf still writing into it would fail the pipeline with
# SIGPIPE, which reads as "no match" and would allow a large write.
if grep -Eq '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}(:[0-9]{2})?' <<<"$content" ||
  grep -Eq '(^|[^0-9a-fA-F])[0-9a-f]{40}([^0-9a-fA-F]|$)' <<<"$content"; then
  echo "blocked: a timestamp or git SHA in $base makes every task that reads it rebuild on every run; inject the stamp in a final uncached step instead" >&2
  exit 2
fi
exit 0
