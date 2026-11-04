#!/usr/bin/env bash
# Refuse one specific command. Deterministic: standard tools only, no network, no secrets.
set -Eeuo pipefail

input="$(cat)"
command=""
if command -v jq >/dev/null 2>&1; then
  command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
elif command -v python3 >/dev/null 2>&1; then
  command="$(printf '%s' "$input" | python3 -c \
    'import json, sys
data = json.load(sys.stdin)
tool = data.get("tool_input") if isinstance(data, dict) else None
print(tool.get("command", "") if isinstance(tool, dict) else "")' || true)"
fi

# Neither parser present: degrade by allowing, because a hook that blocks everything on a
# missing tool is worse than no hook.
case "$command" in
  *"example-forbidden-command"*)
    echo "blocked: say here what to run instead" >&2
    exit 2
    ;;
esac
exit 0
