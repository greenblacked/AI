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
if [ -z "$command" ]; then
  exit 0
fi

# Byte-wise matching (LC_ALL=C): under a UTF-8 locale GNU grep takes quadratic time on the
# verb pattern below, so a large command outlasts the hook timeout, and a timed-out hook
# fails open. Nothing here needs more than ASCII to match.
export LC_ALL=C

# A command that names no protected artifact has nothing to protect; allow it at once.
if ! printf '%s' "$command" | grep -Eq '\.dSYM|mapping\.txt|\.symbols'; then
  exit 0
fi

# A command that names a protected artifact and is too large to scan is refused rather than
# scanned slowly, because a scan that times out allows the deletion.
if [ "$(printf '%s' "$command" | wc -c)" -gt 32768 ]; then
  echo "blocked: the command names a symbol artifact and is larger than 32 KiB, which this hook will not scan. Put the commands in a script file or split them, and archive or upload the symbols instead of deleting them" >&2
  exit 2
fi

# Only a deleting verb is refused; reading or copying a symbol file is fine. The verb may be
# path-qualified (/bin/rm, /usr/bin/unlink) or escaped (\rm) to dodge an alias. It may also be
# the last word (names piped to xargs, arriving on stdin) or followed by ${IFS}.
if printf '%s' "$command" | grep -Eq '(^|[[:space:];&|(\\])([^[:space:];&|()]*/)?(rm|unlink)([[:space:]]|$|\$\{?IFS)|find[[:space:]].*-delete'; then
  echo "blocked: shipped-build symbols are needed to symbolicate crashes; archive or upload them instead of deleting" >&2
  exit 2
fi
exit 0
