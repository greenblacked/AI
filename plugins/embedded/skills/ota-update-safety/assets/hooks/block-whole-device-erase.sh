#!/usr/bin/env bash
# Refuse a whole-device erase or readout-protection write from a debug probe. Deterministic: standard tools only, no network, no secrets.
# It reads the command text and nothing else. It undoes quoting, backslashes and line continuations
# before matching, and refuses a probe command it cannot read (a $'..' escape, a brace expansion, a
# variable or substitution in command position) rather than guessing. A script file the command runs
# and an interpreter one-liner are out of scope: the hook cannot see what they do.
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
# Lower-cased once so every pattern below is case-insensitive without a grep flag. A J-Link
# script argument is dropped first: its file name (erase_all.jlink, no_erase.txt) says nothing
# about what the command line does, and the script's content is not visible here. The argument
# ends at a space, a joiner or a closing parenthesis, so `-CommandFile <(echo erase)` leaves
# `erase)` behind to be matched.
# The piped J-Link form (echo erase | JLinkExe, printf 'erase\n' | JLinkExe, quoted or not) is
# matched; openocd may carry `;` inside a quoted -c argument, so its pattern runs to a pipe or &.
lower="$(printf '%s' "$command" | tr '[:upper:]' '[:lower:]')"
scrub='s/-(commanderscript|commandfile)[[:space:]=]+[^[:space:];&|)]+//g'
scrubbed="$(printf '%s' "$lower" | sed -E "$scrub")"

# A text match cannot read the shell's own spellings, so the patterns run twice: on the command as
# written (the literal \n and quoted forms below need their quotes and backslashes) and on `plain`,
# the command as the shell reads its words. plain joins a backslash-newline continuation, drops the
# $ of $'..' and $"..", and deletes quotes and backslashes, so st-flash era\se, st-flash 'erase' and
# st-flash er""ase are st-flash erase. Newlines stay in plain, because the probe patterns below stop
# at a line end; plain_flat turns them into spaces for the piped J-Link forms.
# What cannot be normalised is refused instead, when the command also names a probe tool or the
# word erase: a $'..' string with a backslash (hex and octal escapes), a brace expansion with a
# comma or `..` outside quotes, and a variable, a command substitution or a backtick where the
# command word goes ($t --eraseall, $(echo st-flash) erase). A variable that is only the start of
# a path ($HOME/bin/nrfjprog) is read as the path it ends in. Indirection through a script file
# or an interpreter one-liner is still out of scope: this hook sees only the command text.
# Standalone like every hook here, so these two functions are copied rather than sourced.
normalise() {
  LC_ALL=C awk '{ if (sub(/\\$/, "")) { buf = buf $0; next } print buf $0; buf = "" } END { if (buf != "") print buf }' |
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
plain="$(printf '%s\n' "$lower" | normalise | sed -E "$scrub")"
plain_flat="$(printf '%s' "$plain" | tr '\n\r' '  ')"
if hits "$plain_flat" -E 'nrfjprog|jlink|pyocd|openocd|st-flash|esptool|stm32_programmer_cli|erase|recover' &&
  unreadable "$lower" "$plain"; then
  echo "blocked: this hook could not read the command (a \$'...' escape, a brace expansion, or a variable or substitution where the command goes) and it names a debug probe or an erase. Write the command plainly, with the tool and its erase option spelled out." >&2
  exit 2
fi

sp='[[:space:]]'
bs='[\\]'
q="[\"']"
word_end="(${sp}|\$|[;&|)])"
# A J-Link command can reach the tool on stdin, so `erase` is also matched as a word wherever it
# starts: after a space, a quote or a literal \n (printf 'r\nerase\nq\n'). What may follow it
# depends on how the commands reach J-Link:
#   - before `;` or `&` it must stand alone, with at most a quote, a parenthesis or a redirect to a
#     file in between (echo erase > c.jlink && JLinkExe -CommandFile c.jlink). Text after `erase`
#     there means `erase` is an argument of some other command (grep -n erase docs.md; JLinkExe).
#   - before a pipe (`|` or `|&`) other words may follow it, because they are the rest of the
#     script that is piped (printf '%s\n' r erase q | JLinkExe). A pipe carries the output of the
#     whole left side, so the words in front of it are what J-Link reads.
#   - in a group, a brace or parenthesis list piped as a whole ({ echo r; echo erase; } | JLinkExe).
#   - in the literal \n form the rest of the script may follow (`erase\nexit\n' | JLinkExe`).
# `erased` and `erase_log` are not the word.
# Real newlines end a command, so the literal-\n form runs on the lines as they are. The other
# forms run on a view with the newlines turned into spaces, which keeps a multi-line quoted
# printf, and a pipe at the end of a line, in one command; the heredoc body is read line by line
# by the awk below, so the text after its delimiter is never part of it.
stdin_erase_lit="(^|${sp}|${q}|${bs}n)erase${bs}n[^|;&]*(;|&+|\\|&?)[^;&]*jlink"
stdin_erase="(^|${sp}|${q}|${bs}n)erase${q}?${sp}*\\)*${sp}*(>>?${sp}*[^[:space:];&|]+${sp}*)?(;|&+)[^;&]*jlink"
stdin_erase_pipe="(^|${sp}|${q}|${bs}n)erase((${sp}|${q})[^|;&]*)?\\|&?[^;&]*jlink"
stdin_erase_group="(^|${sp}|${q}|${bs}n)erase([^[:alnum:]_|{}()][^|{}()]*)?[})]${sp}*\\|&?[^;&]*jlink"
stdin_erase_sq="'(([^'|;&]*${sp})?)erase(${sp}[^'|;&]*)?'${sp}*\\|&?[^;&]*jlink"
stdin_erase_dq="\"(([^\"|;&]*${sp})?)erase(${sp}[^\"|;&]*)?\"${sp}*\\|&?[^;&]*jlink"
# nrfjprog: -e is --eraseall and --chiperase erases the whole flash before --program. pyocd: -m on
# erase is taken from the task brief, not checked against pyocd's own help (not installed here);
# `flash --erase chip` is its chip-erase option. openocd: `flash erase_address` erases a range this
# hook cannot compare with the chip size, so any use of it is refused.
probe=(
  -e "st-flash[^|;&]*${sp}erase${word_end}"
  -e "nrfjprog[^|;&]*(${sp}-e${word_end}|--(eraseall|chiperase|recover|rbp|rdp))"
  -e "esptool[^|;&]*[[:space:]_.-]erase[_-]flash"
  -e "jlink(exe|\.exe)?[^|;&]*(${sp}|${q}|${bs}n)erase(${sp}|\$|[;&|)]|${q}|${bs}n)"
  -e "pyocd[^|;&]*${sp}erase(${sp}[^|;&]*)?${sp}(--chip|--mass|-c|-m)(${sp}|\$|[;&|=])"
  -e "pyocd[^|;&]*${sp}(--erase|-e)(${sp}+|=)chip(${sp}|\$|[;&|)])"
  -e "stm32_programmer_cli[^|;&]*(-e|--erase)${sp}+all"
  -e "stm32_programmer_cli[^|;&]*-ob[^|;&]*(rdp|wrp|optr)"
  -e "openocd[^|&]*(mass_erase|flash${sp}+erase_sector${sp}+0${sp}+0${sp}+last|flash${sp}+erase_address|stm32[a-z0-9]*x${sp}+(lock|option_write|options_write))"
)
stdin_forms=(-e "$stdin_erase" -e "$stdin_erase_pipe" -e "$stdin_erase_group" -e "$stdin_erase_sq" -e "$stdin_erase_dq")
flat="$(printf '%s' "$scrubbed" | tr '\n' ' ')"
hit=0
if hits "$scrubbed" -E "${probe[@]}" -e "$stdin_erase_lit" ||
  hits "$flat" -E "${stdin_forms[@]}"; then
  hit=1
elif [ "$plain" != "$scrubbed" ] &&
  { hits "$plain" -E "${probe[@]}" || hits "$plain_flat" -E "${stdin_forms[@]}"; }; then
  hit=1
fi
# A J-Link heredoc (`JLinkExe <<EOF`, `cat <<EOF | JLinkExe`) or here-string (`JLinkExe <<< erase`)
# is judged by its own lines: the body runs to the delimiter line, and an `erase` after it, or in
# a later command, is not part of what J-Link reads. The delimiter is the word after `<<`, with
# an optional `-`, quotes or a backslash taken off it, and it may be any word: <<@@ and <<$'EOF'
# are read as @@ and EOF. A delimiter that holds a `$` or a backtick, or is missing, cannot be
# read, so the rest of the command is taken as the body. A body counts when it feeds J-Link:
#   - the heredoc line names J-Link before it or pipes it into J-Link;
#   - the line ends in a pipe, and the next line after the delimiter names J-Link
#     (cat <<EOF |, the body, EOF, then JLinkExe);
#   - the body is written to a file (cat <<EOF > cmds.txt, tee cmds.txt <<EOF) and a line that
#     names J-Link names that file too (JLinkExe -CommandFile cmds.txt).
# A heredoc that feeds something else (cat <<EOF, a body with erase, then JLinkExe on its own)
# is not part of what J-Link reads.
if [ "$hit" -eq 0 ]; then
  heredoc="$(LC_ALL=C awk '
    function has_erase(s) { return s ~ /(^|[ \t"\047]|\\n)erase([ \t;&|)"\047]|\\n|$)/ }
    function finish(   k) {
      if (body_erase) {
        if (feeds) hit = 1
        for (k = 1; k <= nt; k++) files[tfs[k]] = 1
        if (piped) pend = 1
      }
      inbody = 0
    }
    {
      line = $0
      if (inbody) {
        if (delim != "") {
          t = line
          sub(/^[ \t]+/, "", t)
          sub(/[ \t\r]+$/, "", t)
          if (t == delim) { finish(); next }
        }
        if (has_erase(line)) body_erase = 1
        next
      }
      if (pend) { pend = 0; if (index(line, "jlink")) hit = 1 }
      if (index(line, "jlink")) jl[++nj] = line
      p = index(line, "<<")
      if (!p) next
      feeds = (line ~ /jlink(exe|\.exe)?[^|;&]*<</ || line ~ /<<.*\|&?[^;&]*jlink/)
      rest = substr(line, p + 2)
      if (substr(rest, 1, 1) == "<") { if (feeds && has_erase(substr(rest, 2))) hit = 1; next }
      nt = 0
      tmp = line
      while (match(tmp, />>?[ \t]*[^ \t;&|<>()]+/)) {
        f = substr(tmp, RSTART, RLENGTH)
        sub(/^>>?[ \t]*/, "", f)
        tfs[++nt] = f
        tmp = substr(tmp, RSTART + RLENGTH)
      }
      tmp = line
      while (match(tmp, /tee[ \t]+(-a[ \t]+)?[^ \t;&|<>()]+/)) {
        f = substr(tmp, RSTART, RLENGTH)
        sub(/^tee[ \t]+(-a[ \t]+)?/, "", f)
        tfs[++nt] = f
        tmp = substr(tmp, RSTART + RLENGTH)
      }
      piped = (line ~ /\|&?[ \t\r]*\\?[ \t\r]*$/)
      sub(/^-/, "", rest)
      sub(/^[ \t]*/, "", rest)
      w = ""
      if (match(rest, /^[^ \t;&|<>()]+/)) w = substr(rest, 1, RLENGTH)
      gsub(/\$["\047]/, "", w)
      gsub(/["\047\\]/, "", w)
      if (w == "" || index(w, "$") || index(w, "`")) delim = ""
      else delim = w
      body_erase = 0
      inbody = 1
    }
    END {
      if (inbody) finish()
      for (f in files) for (k = 1; k <= nj; k++) if (index(jl[k], f)) hit = 1
      print hit ? "hit" : "none"
    }
  ' <<<"$lower")" || heredoc="failed"
  # The awk prints hit or none; no answer means it did not run (the here-string failed to write).
  case "$heredoc" in
    hit) hit=1 ;;
    none) ;;
    *)
      echo "blocked: could not scan the command for a J-Link heredoc (awk gave no answer), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
      exit 2
      ;;
  esac
fi
if [ "$hit" -eq 1 ]; then
  echo "blocked: whole-device erase or readout-protection write. Dump flash and option bytes first (for example 'st-flash read dump.bin 0x08000000 <size>' or 'nrfjprog --readcode dump.hex'), keep the dump, then ask for the erase explicitly." >&2
  exit 2
fi
exit 0
