#!/usr/bin/env bash
# Refuse a terraform or tofu apply that auto-approves or names no existing saved plan file, and a destroy that auto-approves.
# Deterministic: standard tools only, no network, no secrets.
# It reads the command text and nothing else. It undoes quoting, backslashes and line continuations
# before matching, and refuses a command that names terraform or tofu in a spelling it cannot read
# ($'..' escapes, brace expansion, a variable or substitution as the command) rather than guessing.
# A script file the command runs and an interpreter one-liner are out of scope: the hook cannot see
# what they do.
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
[ -n "$command" ] || exit 0

# A text match cannot read the shell's own spellings, so the command is normalised first: a
# backslash-newline continuation is joined, the $ of $'..' and $".." is dropped, and quotes and
# backslashes are deleted, which makes ter""raform, t'o'fu, ter\raform and $'terraform' the binary
# name. Newlines stay in plain (a command word can start a line); plain_flat turns them into
# spaces. What cannot be normalised is refused instead, when the command also names terraform or
# tofu: a $'..' string with a backslash (hex and octal escapes, $'t\x65rraform'), a brace
# expansion with a comma or `..` outside quotes (terraform {apply,}), and a variable, a command
# substitution or a backtick where the command word goes (t=terraform; $t apply). A variable that
# is only the start of a path ($HOME/bin/terraform) is read as the path it ends in. An escape or
# brace can also hide the name itself, so apply or destroy as a word stands in for the name there.
# Indirection through a script file and an interpreter one-liner are out of scope: this hook sees
# only the command text.
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
  cmdpos='(^|[;&|({]|[[:space:]](then|do|else))[[:space:]]*((sudo|command|exec|env|xargs|nohup|time|busybox|builtin)[[:space:]]+)*([$][A-Za-z_][A-Za-z0-9_]*([^/A-Za-z0-9_]|$)|[$]\{[^}]*\}([^/]|$)|[$][(0-9@*]|`)'
  hits "$(printf '%s' "$2" | tr '\n\r' ';;')" -E "$cmdpos"
}
plain="$(printf '%s\n' "$command" | normalise)"
plain_flat="$(printf '%s' "$plain" | tr '\n\r' '  ')"

# A command that names neither terraform nor tofu as a word cannot be an apply, unless a spelling
# hides the name (see above); allow it at once, whatever its size, so a large unrelated command
# is never blocked by this hook.
named=0
if LC_ALL=C hits "$plain_flat" -E '(^|[^[:alnum:]_])(terraform|tofu)([^[:alnum:]_]|$)'; then
  named=1
elif [ "$(printf '%s' "$command" | wc -c)" -le 32768 ] &&
  LC_ALL=C hits "$plain_flat" -E '(^|[^[:alnum:]_])(apply|destroy)([^[:alnum:]_]|$)'; then
  named=2
else
  exit 0
fi

# The word scan below strips quotes with a replacement that is quadratic in a word's length,
# so one enormous token can outlast the hook timeout, and a timed-out hook fails open. Refuse
# an oversized terraform command up front instead; no real invocation is near this size.
if [ "$named" -eq 1 ] && [ "$(printf '%s' "$command" | wc -c)" -gt 32768 ]; then
  echo "blocked: the terraform command is larger than 32 KiB, which this hook will not scan. Put the commands in a script file or split them, and apply only a saved plan file: terraform apply <planfile>" >&2
  exit 2
fi

if LC_ALL=C unreadable "$command" "$plain"; then
  echo "blocked: this hook could not read the command (a \$'...' escape, a brace expansion, or a variable or substitution where the command goes) and it names terraform, tofu, apply or destroy. Write the command plainly, with the binary and its subcommand spelled out, and apply only a saved plan file: terraform apply <planfile>" >&2
  exit 2
fi
[ "$named" -eq 1 ] || exit 0

refuse() {
  echo "blocked: $1. Apply only a saved plan file that a trusted run produced and an approval covered: terraform apply <planfile>" >&2
  exit 2
}

# A destroy with -auto-approve removes everything the state tracks with nobody confirming it; one
# that prompts is allowed.
refuse_destroy() {
  echo "blocked: destroy with -auto-approve. Run terraform destroy without -auto-approve so it prompts, or save a destroy plan (terraform plan -destroy -out <planfile>) and apply that saved plan." >&2
  exit 2
}

# Flags whose value is the next word when written as `-flag value`; that word is not a plan file.
takes_value() {
  case "$1" in
    -var | -var-file | -target | -replace | -parallelism | -lock-timeout | -state | -state-out | -backup | -json-into) return 0 ;;
  esac
  return 1
}

# Sets w to a word as the shell reads it: $'..' and $".." lose their opening, then quotes and
# backslashes are deleted, so $'terraform', ter\raform and "apply" are terraform and apply.
unq() {
  w="${1//\$[\"\']/}"
  w="${w//[\"\'\\]/}"
}

check_segment() {
  local -a words
  local i=0 n w chdir="" seen=0 plan=0 skip=0
  # A failed read leaves no words, which would read as "not an apply" and allow the segment.
  # $1 is a piece of the command, which is at most 32 KiB here (the cap above), so it is always
  # small enough for a here-string. Bash 5.1 and later write one that fits the pipe capacity (64 KiB
  # on Linux) through a pipe and not a temporary file, so the failed temporary-file write that
  # hits() guards against cannot happen on this read; on an older bash it can, and the `|| refuse`
  # below turns that into a block rather than an allow.
  read -ra words <<<"$1" || refuse "could not read the command into words"
  n=${#words[@]}
  # Find `terraform|tofu [-chdir=dir] apply`, tolerating env-var prefixes and a path to the binary.
  while [ "$i" -lt "$n" ]; do
    unq "${words[$i]}"
    case "${w##*/}" in
      terraform | tofu)
        i=$((i + 1))
        while [ "$i" -lt "$n" ]; do
          unq "${words[$i]}"
          case "$w" in
            -chdir=*) chdir="${w#-chdir=}" ;;
            -*) ;;
            *) break ;;
          esac
          i=$((i + 1))
        done
        if [ "$i" -lt "$n" ]; then
          unq "${words[$i]}"
          [ "$w" = "apply" ] && seen=1
          [ "$w" = "destroy" ] && seen=2
        fi
        break
        ;;
    esac
    i=$((i + 1))
  done
  [ "$seen" -ge 1 ] || return 0
  i=$((i + 1))
  while [ "$i" -lt "$n" ]; do
    unq "${words[$i]}"
    i=$((i + 1))
    if [ "$skip" -eq 1 ]; then
      skip=0
      continue
    fi
    case "$w" in
      -auto-approve | -auto-approve=* | --auto-approve | --auto-approve=*)
        if [ "$seen" -eq 2 ]; then refuse_destroy; fi
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
  # A destroy that prompts is allowed, and it takes no plan file.
  [ "$seen" -eq 2 ] || [ "$plan" -eq 1 ] || refuse "apply names no existing saved plan file"
}

while IFS= read -r segment; do
  check_segment "$segment"
done < <(printf '%s\n' "$command" | tr ';&|' '\n\n\n')
exit 0
