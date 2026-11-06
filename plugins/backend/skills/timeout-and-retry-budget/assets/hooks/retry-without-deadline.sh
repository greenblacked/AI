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

# Neither parser present, or nothing readable: allow, because a hook that blocks everything
# on a missing tool is worse than no hook.
case "$path" in
  *.go | *.py | *.ts | *.tsx | *.js | *.jsx | *.mjs | *.cjs | *.java | *.kt | *.scala | *.cs | *.rb | *.php | *.rs | *.yaml | *.yml) ;;
  *) exit 0 ;;
esac

# A retry word has to start a word or an identifier part. Case-insensitively that means
# retry after a non-letter (retry_policy, RETRY_MAX, "retries") or a max_retries / maxAttempts
# prefix; case-sensitively it means a capital R after any letter, the camelCase boundary in
# WaitAndRetryAsync, withRetry and WithMaxRetries. A lowercase run such as "poetry" or
# "geometry" has no capital and is not a boundary. A timeout or deadline anywhere in the text
# satisfies the check, in any casing.
retry_re='(^|[^[:alpha:]])(retr(y|ies|ied|ying)|max_?(retr|attempts))'
camel_re='[[:alpha:]]Retr(y|ies|ied|ying)'
if hits "$text" -Ei "$retry_re" || hits "$text" -E "$camel_re"; then
  if ! hits "$text" -Ei 'timeout|deadline'; then
    echo "blocked: this text sets a retry but no timeout or deadline. Set the timeout from the caller's remaining deadline in the same text, and see call-chain-budget.md." >&2
    exit 2
  fi
fi
exit 0
