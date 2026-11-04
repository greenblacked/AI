#!/usr/bin/env bash
# Refuse a whole-device erase or readout-protection write from a debug probe. Deterministic: standard tools only, no network, no secrets.
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
# Lower-cased once so every pattern below is case-insensitive without a grep flag. A J-Link
# script argument is dropped first: its file name (erase_all.jlink, no_erase.txt) says nothing
# about what the command line does, and the script's content is not visible here.
scrubbed="$(printf '%s' "$command" | tr '[:upper:]' '[:lower:]' |
  sed -E 's/-(commanderscript|commandfile)[[:space:]=]+[^[:space:];&|]+//g')"
sp='[[:space:]]'
word_end="(${sp}|\$|[;&|])"
if printf '%s' "$scrubbed" | grep -Eq \
  -e "st-flash[^|;&]*${sp}erase${word_end}" \
  -e "nrfjprog[^|;&]*--(eraseall|recover|rbp|rdp)" \
  -e "esptool[^|;&]*[[:space:]_.-]erase[_-]flash" \
  -e "jlink(exe|\.exe)?[^|;&]*${sp}erase${word_end}" \
  -e "(^|${sp})erase${sp}*(;|\|)[^;&]*jlink" \
  -e "pyocd[^|;&]*${sp}erase(${sp}[^|;&]*)?${sp}(--chip|--mass|-c)(${sp}|\$|[;&|=])" \
  -e "stm32_programmer_cli[^|;&]*(-e|--erase)${sp}+all" \
  -e "stm32_programmer_cli[^|;&]*-ob[^|;&]*(rdp|wrp|optr)" \
  -e "openocd[^|;&]*(mass_erase|flash${sp}+erase_sector${sp}+0${sp}+0${sp}+last|stm32[a-z0-9]*x${sp}+(lock|option_write|options_write))"; then
  echo "blocked: whole-device erase or readout-protection write. Dump flash and option bytes first (for example 'st-flash read dump.bin 0x08000000 <size>' or 'nrfjprog --readcode dump.hex'), keep the dump, then ask for the erase explicitly." >&2
  exit 2
fi
exit 0
