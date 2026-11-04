#!/usr/bin/env bash
# Refuse a command that deletes a dSYM bundle, an R8 mapping.txt or a .symbols archive. Deterministic: standard tools only, no network, no secrets.
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
  command="$(printf '%s' "$input" | python3 -c \
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
if [ -z "$command" ]; then
  exit 0
fi

# Only a deleting verb is refused; reading or copying a symbol file is fine.
if printf '%s' "$command" | grep -Eq '(^|[[:space:];&|(])(rm|unlink)[[:space:]]|find[[:space:]].*-delete'; then
  if printf '%s' "$command" | grep -Eq '\.dSYM|mapping\.txt|\.symbols'; then
    echo "blocked: shipped-build symbols are needed to symbolicate crashes; archive or upload them instead of deleting" >&2
    exit 2
  fi
fi
exit 0
