#!/usr/bin/env bash
# Require a placeholder list in application files that carry [TK: ...] markers.
# Deterministic: standard tools only, no network, no secrets.
set -Eeuo pipefail

input="$(cat)"
file=""
# Either parser prints nothing for input it cannot read a path from; the hook then allows.
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

# Neither parser present, or no path: allow, because a hook that blocks on a missing
# tool is worse than none.
[ -n "$file" ] || exit 0

case "$file" in
  */applications/*.md | */cv/*.md | applications/*.md | cv/*.md) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

if grep -qF '[TK:' -- "$file" && ! grep -q '## Placeholders to fill' -- "$file"; then
  echo "The write already happened; this is a correction, not a block. $file contains a [TK: ...] placeholder but no '## Placeholders to fill' section. Add that section listing each placeholder with the question that fills it." >&2
  exit 2
fi
exit 0
