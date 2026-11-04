#!/usr/bin/env bash
# Refuse a source-file write that sets a retry and no deadline in the same text.
# Deterministic: standard tools only, no network, no secrets.
# Limit: an Edit fragment that adds only a retry, with its timeout elsewhere in the file,
# is refused, so write the timeout into the fragment.
set -Eeuo pipefail

input="$(cat)"
path=""
text=""
if command -v jq >/dev/null 2>&1; then
  path="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.file_path | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
  text="$(printf '%s' "$input" | jq -r \
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
  text="$(printf '%s' "$input" | python3 -I -c \
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

# Neither parser present, or nothing readable: allow, because a hook that blocks everything
# on a missing tool is worse than no hook.
case "$path" in
  *.go | *.py | *.ts | *.tsx | *.js | *.jsx | *.mjs | *.cjs | *.java | *.kt | *.scala | *.cs | *.rb | *.php | *.rs | *.yaml | *.yml) ;;
  *) exit 0 ;;
esac

# Case-insensitive, and a retry word has to start a word or an identifier part (so "entry"
# or "geometry" do not count, while max_retries, maxRetries and RetryPolicy do). A timeout or
# deadline anywhere in the text satisfies the check, in any casing.
retry_re='(^|[^[:alpha:]])(retr(y|ies|ied|ying)|max_?(retr|attempts))'
if printf '%s' "$text" | grep -Eqi "$retry_re"; then
  if ! printf '%s' "$text" | grep -Eqi 'timeout|deadline'; then
    echo "blocked: this text sets a retry but no timeout or deadline. Set the timeout from the caller's remaining deadline in the same text, and see call-chain-budget.md." >&2
    exit 2
  fi
fi
exit 0
