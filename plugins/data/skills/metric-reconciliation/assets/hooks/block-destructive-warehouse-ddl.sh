#!/usr/bin/env bash
# Refuse a command that drops or truncates a warehouse object. Deterministic: standard tools
# only, no network, no secrets. One text match, not a SQL parser: DDL written to a file and run
# later passes, and a prose mention in the command also blocks, which is the safe direction.
# It does not replace db-migration, which governs application-database schema changes.
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
# missing tool is worse than none.
if [ -z "$command" ]; then
  if ! command -v jq >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
    echo "block-destructive-warehouse-ddl: neither jq nor python3 found, allowing" >&2
  fi
  exit 0
fi

# Word-bounded and SQL-shaped, so "truncated" and `truncate -s 0 file` pass while
# `TRUNCATE TABLE t`, `truncate t` and `DROP MATERIALIZED VIEW v` block.
drop_re='\<drop[[:space:]]+((external|materialized|temp|temporary)[[:space:]]+)?(table|view|schema|database|column)\>'
truncate_re='\<truncate[[:space:]]+(table[[:space:]]+)?[[:alpha:]_"`[\\]'
bq_re='\<bq[[:space:]]+rm\>'
if printf '%s' "$command" | grep -Eqi -e "$drop_re" -e "$truncate_re" -e "$bq_re"; then
  echo "blocked: destructive warehouse DDL (DROP TABLE/VIEW/SCHEMA/DATABASE/COLUMN, TRUNCATE, bq rm). Rename the object, archive it, and run the drop yourself after the brownout." >&2
  exit 2
fi
exit 0
