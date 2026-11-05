#!/usr/bin/env bash
# Refuse a command that deletes a dSYM bundle, an R8 mapping.txt or a .symbols archive. Deterministic: standard tools only, no network, no secrets.
# It reads the command text and nothing else. It undoes quoting, backslashes and line continuations
# before matching, and refuses a command that names a symbol artifact in a spelling it cannot read
# ($'..' escapes, brace expansion, a variable or substitution as the command) rather than guessing.
# A script file the command runs and an interpreter one-liner (python3 -c 'os.unlink(...)') are out
# of scope: the hook cannot see what they do.
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

# Neither parser present: degrade by allowing, because a hook that blocks everything on a
# missing tool is worse than no hook.
if [ -z "$command" ]; then
  exit 0
fi

# Byte-wise matching (LC_ALL=C): under a UTF-8 locale GNU grep takes quadratic time on the
# verb pattern below, so a large command outlasts the hook timeout, and a timed-out hook
# fails open. Nothing here needs more than ASCII to match.
export LC_ALL=C

# A text match cannot read the shell's own spellings, so the command is normalised first: a
# backslash-newline continuation is joined, the $ of $'..' and $".." is dropped, and quotes and
# backslashes are deleted, which makes "rm", 'rm', r""m, r\m and $'rm' the verb, and App.d"SY"M the
# artifact. Newlines stay in plain (a command word can start a line); plain_flat turns them into
# spaces. What cannot be normalised is refused instead, when the command also names a symbol
# artifact: a $'..' string with a backslash (hex and octal escapes, $'r\x6d'), a brace expansion
# with a comma or `..` outside quotes (build/App.{app,dSYM}), and a variable, a command
# substitution or a backtick where the command word goes ($t -rf App.dSYM). A variable that is
# only the start of a path ($HOME/bin/tidy) is read as the path it ends in. Indirection through a
# script file and an interpreter one-liner (python3 -c 'os.unlink(...)') are out of scope: this
# hook sees only the command text, and it refuses only the deleting verbs listed below (rm,
# unlink, find -delete, shred -u, truncate to size zero).
# Standalone like every hook here, so these two functions are copied rather than sourced.
normalise() {
  awk '{ if (sub(/\\$/, "")) { buf = buf $0; next } print buf $0; buf = "" } END { if (buf != "") print buf }' |
    sed -E "s/[\$][\"']//g" | tr -d "\"'\\\\"
}
# unreadable ORIGINAL PLAIN: succeeds when the command uses a spelling that normalise cannot read.
unreadable() {
  local outside cmdpos
  if hits "$1" -E "[\$]'[^']*[\\\\]"; then return 0; fi
  outside="$(printf '%s' "$1" | sed -E "s/'[^']*'|\"[^\"]*\"//g")"
  if hits "$outside" -E '(^|[^$])\{[^{}[:space:]]*(,|\.\.)[^{}[:space:]]*\}'; then return 0; fi
  cmdpos='(^|[;&|`]|[$][(]|[[:space:]](then|do|else))[[:space:]]*([({][[:space:]]*)*((sudo|command|exec|env|xargs|nohup|time|busybox|builtin)[[:space:]]+)*([$][A-Za-z_][A-Za-z0-9_]*([^/A-Za-z0-9_]|$)|[$]\{[^}]*\}([^/]|$)|[$][(0-9@*]|`)'
  hits "$(printf '%s' "$2" | tr '\n\r' ';;')" -E "$cmdpos"
}
plain="$(printf '%s\n' "$command" | normalise)"
plain_flat="$(printf '%s' "$plain" | tr '\n\r' '  ')"

# A command that names no protected artifact has nothing to protect; allow it at once. The
# artifact may be written in a way only the unreadable spellings can split (App.{app,dSYM}), so
# a looser name is also a reason to look, and only for the refusal below.
named=0
if hits "$plain_flat" -E '\.dSYM|mapping\.txt|\.symbols'; then
  named=1
elif hits "$plain_flat" -iE 'dsym|mapping[.{,]|[.,{]symbols'; then
  named=2
else
  exit 0
fi

# A command that names a protected artifact and is too large to scan is refused rather than
# scanned slowly, because a scan that times out allows the deletion.
if [ "$named" -eq 1 ] && [ "$(printf '%s' "$command" | wc -c)" -gt 32768 ]; then
  echo "blocked: the command names a symbol artifact and is larger than 32 KiB, which this hook will not scan. Put the commands in a script file or split them, and archive or upload the symbols instead of deleting them" >&2
  exit 2
fi

if unreadable "$command" "$plain"; then
  echo "blocked: this hook could not read the command (a \$'...' escape, a brace expansion, or a variable or substitution where the command goes) and it names a symbol artifact. Write the command plainly, so it can be seen whether it deletes the symbols; archive or upload them instead of deleting." >&2
  exit 2
fi
# The looser name only widens what is refused as unreadable; deleting a file that merely has dsym in
# its name is not this hook's business.
[ "$named" -eq 1 ] || exit 0

# Only a deleting verb is refused; reading or copying a symbol file is fine. The verb may be
# path-qualified (/bin/rm, /usr/bin/unlink) or escaped (\rm) to dodge an alias. It may also be
# the last word (names piped to xargs, arriving on stdin) or followed by ${IFS}. shred -u removes
# its target after overwriting it, and truncate to size zero empties a file that stays on disk.
verb='(^|[[:space:];&|(])([^[:space:];&|()]*/)?(rm|unlink)([[:space:]]|$|\$\{?IFS)'
find_delete='find[[:space:]].*-delete'
shred_u='(^|[[:space:];&|(])([^[:space:];&|()]*/)?shred[[:space:]]([^;&|]*[[:space:]])?(-[A-Za-z]*u[A-Za-z]*|--remove)([[:space:]=]|$)'
truncate_0='(^|[[:space:];&|(])([^[:space:];&|()]*/)?truncate[[:space:]]([^;&|]*[[:space:]])?(-s[[:space:]]*0|--size[[:space:]=]+0)([[:space:]]|$)'
if hits "$plain_flat" -E -e "$verb" -e "$find_delete" -e "$shred_u" -e "$truncate_0"; then
  echo "blocked: shipped-build symbols are needed to symbolicate crashes; archive or upload them instead of deleting" >&2
  exit 2
fi
exit 0
