#!/usr/bin/env bash
# Refuse a terraform or tofu apply that auto-approves or names no existing saved plan file.
# Deterministic: standard tools only, no network, no secrets.
set -Eeuo pipefail

input="$(cat)"
command=""
# Either parser prints nothing, and the hook allows, for input it cannot read a command from:
# invalid JSON, JSON that is not an object, a missing or non-object `tool_input`, or a null
# `command`. Erroring out instead would report a failure over a payload it never needed.
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
print(value if isinstance(value, str) else json.dumps(value))' || true)"
fi

# Neither parser present: degrade by allowing, because a hook that blocks everything on a
# missing tool is worse than no hook.
[ -n "$command" ] || exit 0

# The word scan below strips quotes with a replacement that is quadratic in a word's length,
# so one enormous token can outlast the hook timeout, and a timed-out hook fails open. Refuse
# an oversized command up front instead; no real terraform invocation is near this size.
if [ "$(printf '%s' "$command" | wc -c)" -gt 32768 ]; then
  echo "blocked: the command is larger than 32 KiB, which this hook will not scan. Put the commands in a script file or split them, and apply only a saved plan file: terraform apply <planfile>" >&2
  exit 2
fi

refuse() {
  echo "blocked: $1. Apply only a saved plan file that a trusted run produced and an approval covered: terraform apply <planfile>" >&2
  exit 2
}

# Flags whose value is the next word when written as `-flag value`; that word is not a plan file.
takes_value() {
  case "$1" in
    -var | -var-file | -target | -replace | -parallelism | -lock-timeout | -state | -state-out | -backup | -json-into) return 0 ;;
  esac
  return 1
}

check_segment() {
  local -a words
  local i=0 n w chdir="" seen=0 plan=0 skip=0
  read -ra words <<<"$1" || true
  n=${#words[@]}
  # Find `terraform|tofu [-chdir=dir] apply`, tolerating env-var prefixes and a path to the binary.
  while [ "$i" -lt "$n" ]; do
    w="${words[$i]//[\"\']/}"
    case "${w##*/}" in
      terraform | tofu)
        i=$((i + 1))
        while [ "$i" -lt "$n" ]; do
          w="${words[$i]//[\"\']/}"
          case "$w" in
            -chdir=*) chdir="${w#-chdir=}" ;;
            -*) ;;
            *) break ;;
          esac
          i=$((i + 1))
        done
        [ "$i" -lt "$n" ] && [ "${words[$i]//[\"\']/}" = "apply" ] && seen=1
        break
        ;;
    esac
    i=$((i + 1))
  done
  [ "$seen" -eq 1 ] || return 0
  i=$((i + 1))
  while [ "$i" -lt "$n" ]; do
    w="${words[$i]//[\"\']/}"
    i=$((i + 1))
    if [ "$skip" -eq 1 ]; then
      skip=0
      continue
    fi
    case "$w" in
      -auto-approve | -auto-approve=* | --auto-approve | --auto-approve=*)
        refuse "apply with -auto-approve"
        ;;
      -*=*) ;;
      -*)
        if takes_value "${w#-}" || takes_value "$w"; then skip=1; fi
        ;;
      *)
        if [ -f "${chdir:+$chdir/}$w" ]; then plan=1; fi
        ;;
    esac
  done
  [ "$plan" -eq 1 ] || refuse "apply names no existing saved plan file"
}

while IFS= read -r segment; do
  check_segment "$segment"
done < <(printf '%s\n' "$command" | tr ';&|' '\n\n\n')
exit 0
