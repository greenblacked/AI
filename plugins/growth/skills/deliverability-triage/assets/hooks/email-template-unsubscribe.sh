#!/usr/bin/env bash
# Refuse a marketing email template written without an unsubscribe reference. Deterministic:
# standard tools only, no network, no secrets. Covers Write only, not Edit or MultiEdit.
set -Eeuo pipefail

input="$(cat)"
file_path=""
content=""
# Either parser prints nothing, and the hook allows, for input it cannot read: invalid
# JSON, a non-object, a missing tool_input, or non-string fields.
if command -v jq >/dev/null 2>&1; then
  file_path="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.file_path | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
  content="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.content | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  parse='import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
value = tool.get(sys.argv[1]) if isinstance(tool, dict) else None
print(value if isinstance(value, str) else "")'
  file_path="$(printf '%s' "$input" | python3 -I -c "$parse" file_path || true)"
  content="$(printf '%s' "$input" | python3 -I -c "$parse" content || true)"
fi

# hits TEXT GREP-OPTION...: succeeds when grep finds a match in TEXT, fails when it finds none, and
# refuses the command on any other outcome. TEXT reaches grep as a here-string, not through a pipe:
# grep quits early under -q, and a writer piped into it would then die of SIGPIPE, which pipefail
# turns into a failed pipeline that reads as "no match". Bash writes a large here-string to a
# temporary file; when that write fails (a full disk, a file-size limit) the redirection fails with
# status 1 and grep never runs, which `if grep ...` would also read as "no match" and allow.
# grep -c prints a count even for no match, so no count means grep did not run. Only status 0 with
# a count or status 1 with a count of 0 is an answer. Standalone like every hook here, so this
# function is copied rather than sourced.
hits() {
  local text=$1 count rc=0
  shift
  count="$(grep -c "$@" <<<"$text")" || rc=$?
  case "$rc:$count" in
    0:[1-9]*) return 0 ;;
    1:0) return 1 ;;
  esac
  echo "blocked: could not scan the text with grep (status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
}

# Neither parser present, or nothing to judge: allow, because a hook that blocks everything
# on a missing tool is worse than no hook.
[ -n "$file_path" ] || exit 0

case "$file_path" in
  emails/marketing/* | */emails/marketing/* | \
    email-templates/marketing/* | */email-templates/marketing/* | \
    templates/email/marketing/* | */templates/email/marketing/*) ;;
  *) exit 0 ;;
esac

if hits "$content" -i 'unsubscribe'; then
  exit 0
fi
echo "blocked: a marketing email template needs an unsubscribe reference (link or List-Unsubscribe). Add one to the content of this write." >&2
exit 2
