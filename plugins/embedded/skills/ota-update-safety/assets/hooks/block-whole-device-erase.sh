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
# about what the command line does, and the script's content is not visible here. The argument
# ends at a space, a joiner or a closing parenthesis, so `-CommandFile <(echo erase)` leaves
# `erase)` behind to be matched.
# The piped J-Link form (echo erase | JLinkExe, printf 'erase\n' | JLinkExe, quoted or not) is
# matched; openocd may carry `;` inside a quoted -c argument, so its pattern runs to a pipe or &.
scrubbed="$(printf '%s' "$command" | tr '[:upper:]' '[:lower:]' |
  sed -E 's/-(commanderscript|commandfile)[[:space:]=]+[^[:space:];&|)]+//g')"
sp='[[:space:]]'
bs='[\\]'
q="[\"']"
word_end="(${sp}|\$|[;&|)])"
# A J-Link command can reach the tool on stdin, so `erase` is also matched as a word wherever it
# starts: after a space, a quote or a literal \n (printf 'r\nerase\nq\n'), and it must be the
# command that is piped or joined: `erase` directly followed by a pipe, `;` or `&`, with at most
# a quote, a parenthesis or a redirect to a file in between (echo erase > c.jlink && JLinkExe
# -CommandFile c.jlink). Text after `erase` is allowed only in the literal \n form, where it is
# the rest of the script (`erase\nexit\n' | JLinkExe`); anywhere else it means `erase` is an
# argument of some other command (grep -n erase docs.md; JLinkExe ...) and is not matched.
# `erased` and `erase_log` are not the word.
# Real newlines end a command, so the literal-\n form runs on the lines as they are. The other
# forms run on a view with the newlines turned into spaces, which keeps a multi-line quoted
# printf, and a pipe at the end of a line, in one command; the heredoc body is read line by line
# by the awk below, so the text after its delimiter is never part of it.
flat="$(printf '%s' "$scrubbed" | tr '\n' ' ')"
stdin_erase_lit="(^|${sp}|${q}|${bs}n)erase${bs}n[^|;&]*(;|&+|\\|)[^;&]*jlink"
stdin_erase="(^|${sp}|${q}|${bs}n)erase${q}?${sp}*\\)*${sp}*(>>?${sp}*[^[:space:];&|]+${sp}*)?(;|&+|\\|)[^;&]*jlink"
stdin_erase_sq="'(([^'|;&]*${sp})?)erase(${sp}[^'|;&]*)?'${sp}*\\|[^;&]*jlink"
stdin_erase_dq="\"(([^\"|;&]*${sp})?)erase(${sp}[^\"|;&]*)?\"${sp}*\\|[^;&]*jlink"
# The text reaches grep as a here-string, not through a pipe: grep -q quits at its first match,
# and under pipefail a printf still writing into it would fail the pipeline with SIGPIPE, which
# reads as "no match" and would allow a large command.
if grep -Eq \
  -e "st-flash[^|;&]*${sp}erase${word_end}" \
  -e "nrfjprog[^|;&]*--(eraseall|recover|rbp|rdp)" \
  -e "esptool[^|;&]*[[:space:]_.-]erase[_-]flash" \
  -e "jlink(exe|\.exe)?[^|;&]*(${sp}|${q}|${bs}n)erase(${sp}|\$|[;&|)]|${q}|${bs}n)" \
  -e "pyocd[^|;&]*${sp}erase(${sp}[^|;&]*)?${sp}(--chip|--mass|-c)(${sp}|\$|[;&|=])" \
  -e "stm32_programmer_cli[^|;&]*(-e|--erase)${sp}+all" \
  -e "stm32_programmer_cli[^|;&]*-ob[^|;&]*(rdp|wrp|optr)" \
  -e "openocd[^|&]*(mass_erase|flash${sp}+erase_sector${sp}+0${sp}+0${sp}+last|stm32[a-z0-9]*x${sp}+(lock|option_write|options_write))" \
  -e "$stdin_erase_lit" \
  <<<"$scrubbed" ||
  grep -Eq -e "$stdin_erase" -e "$stdin_erase_sq" -e "$stdin_erase_dq" <<<"$flat"; then
  hit=1
else
  hit=0
fi
# A J-Link heredoc (`JLinkExe <<EOF`, `cat <<EOF | JLinkExe`) or here-string (`JLinkExe <<< erase`)
# is judged by its own lines: the body runs to the delimiter line, and an `erase` after it, or in
# a later command, is not part of what J-Link reads. The delimiter is the word after `<<`, with
# an optional `-`, quotes or a backslash.
if [ "$hit" -eq 0 ]; then
  heredoc="$(LC_ALL=C awk '
    function has_erase(s) { return s ~ /(^|[ \t"\047]|\\n)erase([ \t;&|)"\047]|\\n|$)/ }
    {
      line = $0
      if (delim != "") {
        t = line
        sub(/^[ \t]+/, "", t)
        sub(/[ \t\r]+$/, "", t)
        if (t == delim) { delim = ""; next }
        if (has_erase(line)) hit = 1
        next
      }
      p = index(line, "<<")
      if (!p) next
      if (line !~ /jlink(exe|\.exe)?[^|;&]*<</ && line !~ /<<.*\|[^;&]*jlink/) next
      rest = substr(line, p + 2)
      if (substr(rest, 1, 1) == "<") { if (has_erase(substr(rest, 2))) hit = 1; next }
      sub(/^-/, "", rest)
      sub(/^[ \t]*/, "", rest)
      sub(/^["\047\\]+/, "", rest)
      if (match(rest, /^[a-z0-9_.-]+/)) delim = substr(rest, 1, RLENGTH)
    }
    END { print hit ? "hit" : "none" }
  ' <<<"$scrubbed")" || heredoc="failed"
  case "$heredoc" in
    hit) hit=1 ;;
    none) ;;
    *)
      echo "blocked: could not scan the command for a J-Link heredoc, so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
      exit 2
      ;;
  esac
fi
if [ "$hit" -eq 1 ]; then
  echo "blocked: whole-device erase or readout-protection write. Dump flash and option bytes first (for example 'st-flash read dump.bin 0x08000000 <size>' or 'nrfjprog --readcode dump.hex'), keep the dump, then ask for the erase explicitly." >&2
  exit 2
fi
exit 0
