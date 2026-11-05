#!/usr/bin/env bash
# Refuse a whole-device erase or readout-protection write from a debug probe. Deterministic: standard tools only, no network, no secrets.
# It reads the command text and nothing else. It undoes quoting, backslashes and line continuations
# before matching, and refuses a probe command it cannot read (a $'..' escape, a brace expansion, a
# variable or substitution in command position, which is read right after a separator or after
# sudo, exec, command, env and similar wrappers, not after other wrappers) rather than guessing. A script file the command runs
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
[ -n "$command" ] || exit 0
# Lower-cased once so every pattern below is case-insensitive without a grep flag. A J-Link
# script argument is dropped first: its file name (erase_all.jlink, no_erase.txt) says nothing
# about what the command line does, and the script's content is not visible here. The argument
# ends at a space, a joiner or a closing parenthesis, so `-CommandFile <(echo erase)` leaves
# `erase)` behind to be matched.
# The piped J-Link form (echo erase | JLinkExe, printf 'erase\n' | JLinkExe, quoted or not) is
# matched; openocd may carry `;` inside a quoted -c argument, so its pattern runs to a pipe or &.
# Byte-wise matching (LC_ALL=C): under a UTF-8 locale GNU grep takes quadratic time on the
# patterns below for a command with tens of thousands of J-Link commands, so a large command
# outlasts the hook timeout, and a timed-out hook fails open. Nothing here needs more than ASCII
# to match, and upper case is only folded for ASCII, which is all a tool name or option uses.
export LC_ALL=C
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
# command word goes (right after a separator, a group opener, then, do or else, or one of the wrappers sudo, command, exec, env, xargs, nohup, time, busybox and builtin, with any NAME=value assignments between; a command run through another wrapper is not read) ($t --eraseall, $(echo st-flash) erase). A variable that is only the start of
# a path ($HOME/bin/nrfjprog) is read as the path it ends in. Indirection through a script file
# or an interpreter one-liner is still out of scope: this hook sees only the command text.
# Standalone like every hook here, so these two functions are copied rather than sourced.
# A line continues only when it ends in an odd number of backslashes: `\\` is an escaped backslash and the
# command ends there. The run is counted from the end, so a long run costs time in its own length only.
# A line that would join and has a # at the start of a word (after the line start, a space or a shell
# operator, quoted or not) is uncertain: bash does not join a comment line and does join a quoted
# # such as 'a # b', and the hook does not track quotes. For such a command the output holds both
# readings, one after the other, joined and then unjoined, so a rule that refuses either one
# refuses the command. Lines without such a # keep the single joined reading.
normalise() {
  LC_ALL=C awk '{ n = length($0); k = 0; while (k < n && substr($0, n - k, 1) == "\\") k++; if (k % 2) { body = substr($0, 1, n - 1); printf "%s", body; cont = 1; if ($0 ~ /(^|[ \t\r;&|()<>`])#/) { unc = 1; b[++m] = body "\n" } else b[++m] = body; next } print; b[++m] = $0 "\n"; cont = 0 } END { if (cont) { print ""; b[++m] = "\n" } if (unc) for (i = 1; i <= m; i++) printf "%s", b[i] }' |
    sed -E "s/[\$][\"']//g" | tr -d "\"'\\\\"
}
# unreadable ORIGINAL PLAIN: succeeds when the command uses a spelling that normalise cannot read.
unreadable() {
  local outside cmdpos
  if hits "$1" -E "[\$]'[^']*[\\\\]"; then return 0; fi
  outside="$(printf '%s' "$1" | sed -E "s/'[^']*'|\"[^\"]*\"//g")"
  if hits "$outside" -E '(^|[^$])\{[^{}[:space:]]*(,|\.\.)[^{}[:space:]]*\}'; then return 0; fi
  cmdpos='(^|[;&|`]|[$][(]|[[:space:]](then|do|else))[[:space:]]*([({][[:space:]]*)*((sudo|command|exec|e[n]v|xargs|nohup|time|busybox|builtin|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*)[[:space:]]+)*([$][A-Za-z_][A-Za-z0-9_]*([^/A-Za-z0-9_]|$)|[$]\{[^}]*\}([^/]|$)|[$][(0-9@*]|`)'
  hits "$(printf '%s' "$2" | tr '\n\r' ';;')" -E "$cmdpos"
}
# normalise needs awk. Without it the pipeline below fails with status 127, which is not a block,
# so the command would run unjudged; refuse instead, because a missing tool is not a reason to allow.
if [ -n "$command" ] && ! command -v awk >/dev/null 2>&1; then
  echo "blocked: awk is not installed, so this hook cannot read the command and did not judge it. Install awk (any POSIX awk), or run the command yourself." >&2
  exit 2
fi
plain_ns="$(printf '%s\n' "$lower" | normalise)"
plain="$(printf '%s\n' "$plain_ns" | sed -E "$scrub")"
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
#   - before `;` or `&` it must stand alone, with at most a quote or a parenthesis in between
#     (echo erase; JLinkExe). Text after `erase` there means `erase` is an argument of some other
#     command (grep -n erase docs.md; JLinkExe). An erase written to a file (echo erase > c.jlink,
#     printf '%s\n' r erase q | tee c.jlink) is not read here: it counts only when a J-Link line
#     names that file, which the awk below checks, so a file J-Link never reads is not a block.
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
stdin_erase="(^|${sp}|${q}|${bs}n)erase${q}?${sp}*\\)*${sp}*(;|&+)[^;&]*jlink"
stdin_erase_pipe="(^|${sp}|${q}|${bs}n)erase((${sp}|${q})[^|;&]*)?\\|&?[^;&]*jlink"
stdin_erase_group="(^|${sp}|${q}|${bs}n)erase([^[:alnum:]_|{}()][^|{}()]*)?[})]${sp}*\\|&?[^;&]*jlink"
stdin_erase_sq="'(([^'|;&]*${sp})?)erase(${sp}[^'|;&]*)?'${sp}*\\|&?[^;&]*jlink"
stdin_erase_dq="\"(([^\"|;&]*${sp})?)erase(${sp}[^\"|;&]*)?\"${sp}*\\|&?[^;&]*jlink"
# nrfjprog: -e is --eraseall, --chiperase erases the whole flash before --program, and the QSPI
# forms (--qspichiperase, --qspieraseall) erase the external flash; --sectorerase is not matched.
# pyocd: `erase` takes -c/--chip and --mass for a chip erase (argparse also accepts a unique prefix
# of a long option, so --ch, --chi, --ma and --mas count; pyocd has no -m), and `flash`/`load` take
# --erase chip, which may be written -e chip, -echip or -e=chip; --erase sector and -s are not
# matched. openocd: `mass_erase` is a whole word in every driver (stm32f1x mass_erase 0,
# nrf5 mass_erase), and erase_sector with the first sector 0 and `last` covers a whole bank.
# `flash erase_address` is judged separately below, because it erases a range this hook cannot
# compare with the chip size.
probe=(
  -e "st-flash[^|;&]*${sp}erase${word_end}"
  -e "nrfjprog[^|;&]*(${sp}-e${word_end}|--(eraseall|chiperase|qspichiperase|qspieraseall|recover|rbp|rdp))"
  -e "esptool[^|;&]*[[:space:]_.-]erase[_-]flash"
  -e "jlink(exe|\.exe)?[^|;&]*(${sp}|${q}|${bs}n)erase(${sp}|\$|[;&|)]|${q}|${bs}n)"
  -e "pyocd[^|;&]*${sp}erase(${sp}[^|;&]*)?${sp}(-c|--ch(ip|i)?|--ma(ss?)?)(${sp}|\$|[;&|=])"
  -e "pyocd[^|;&]*${sp}(--er(a|as|ase)?(${sp}+|=)|-e(${sp}*|=))chip(${sp}|\$|[;&|)])"
  -e "stm32_programmer_cli[^|;&]*(-e|--erase)${sp}+all"
  -e "stm32_programmer_cli[^|;&]*-ob[^|;&]*(rdp|wrp|optr)"
  -e "openocd[^|&]*([^[:alnum:]_]mass_erase([^[:alnum:]_]|\$)|flash${sp}+erase_sector${sp}+[^[:space:]]+${sp}+0${sp}+last|stm32[a-z0-9]*x${sp}+(lock|option_write|options_write))"
)
range_probe=(-e "openocd[^|&]*flash${sp}+erase_address")
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
# A range erase is a different refusal from a whole-device one; it is only looked for when the
# whole-device patterns found nothing.
if [ "$hit" -eq 0 ] &&
  { hits "$scrubbed" -E "${range_probe[@]}" ||
    { [ "$plain" != "$scrubbed" ] && hits "$plain" -E "${range_probe[@]}"; }; }; then
  hit=3
fi
# A J-Link heredoc (`JLinkExe <<EOF`, `cat <<EOF | JLinkExe`) or here-string (`JLinkExe <<< erase`)
# is judged by its own lines: the body runs to the delimiter line, and an `erase` after it, or in
# a later command, is not part of what J-Link reads. The delimiter is the word after `<<`, with
# an optional `-`, quotes or a backslash taken off it, and it may be any word: <<@@ and <<$'EOF'
# are read as @@ and EOF. The delimiter line is the delimiter and nothing else, as bash reads it:
# a trailing space or carriage return, or any indent, makes it an ordinary body line, and only
# `<<-` lets the line start with tabs. A delimiter that holds a `$` or a backtick, or is missing,
# cannot be read, so the rest of the command is taken as the body. A body counts when it feeds
# J-Link:
#   - the heredoc line names J-Link before it or pipes it into J-Link;
#   - the line ends in a pipe, and the next line after the delimiter names J-Link
#     (cat <<EOF |, the body, EOF, then JLinkExe);
#   - the body is written to a file (cat <<EOF > cmds.txt, tee cmds.txt <<EOF) and a command that
#     names J-Link names that file too (JLinkExe -CommandFile cmds.txt).
# A heredoc that feeds something else (cat <<EOF, a body with erase, then JLinkExe on its own)
# is not part of what J-Link reads.
# An erase that echo or printf writes to a file (echo erase > c.jlink, printf '%s\n' r erase q >>
# c.jlink, echo erase | tee c.jlink) counts the same way: when a command that names J-Link names
# that file, joined by ; or && or only by a line break. The redirect may touch the word (echo
# erase>c.jlink), follow a descriptor copy (echo erase 2>&1 > c.jlink), be written >| or &>, or
# follow a here-string (cat <<< erase > c.jlink). An escaped \> that touches the word
# (erase\>c.jlink) is an argument, not a redirect; a spaced \> (erase \> c.jlink) is still read as a
# redirect, which fails closed.
# Names are compared as whole words, a path
# by its last component, so a file called a is not found in every command. Each J-Link command
# is looked at once, with the file names it redirects its own output to taken out, and each
# file name is looked up in a table, so the work grows with the length of the command and not
# with the files times the commands.
esc_mark=$'\001'
esc_pair=$'\002'
jl_scan() {
  LC_ALL=C awk '
    function has_erase(s) { return s ~ /(^|[ \t"\047]|\\n)erase([ \t\r;&|)"\047<>]|\\n|$)/ }
    function redir(s,   out, r) {
      # >&N and >&N- copy a descriptor only when the digits or dash are the whole word; >&1c.jlink
      # writes stdout and stderr to a file called 1c.jlink, so that text stays.
      out = ""
      while (match(s, /[0-9]*>&[0-9]+-?/)) {
        r = substr(s, RSTART + RLENGTH, 1)
        if (r == "" || r ~ /[ \t\r;&|()<>]/) out = out substr(s, 1, RSTART - 1) " "
        else out = out substr(s, 1, RSTART + RLENGTH - 1)
        s = substr(s, RSTART + RLENGTH)
      }
      s = out s
      gsub(/>&/, ">", s)
      gsub(/&>/, ">", s)
      gsub(/>\|/, ">", s)
      return s
    }
    function hs_erase(s,   w, c) {
      sub(/^[ \t]+/, "", s)
      c = substr(s, 1, 1)
      if (c == "\"" || c == "\047") { w = substr(s, 2); sub(c ".*$", "", w) }
      else { w = s; sub(/[ \t;&|<>()].*$/, "", w) }
      return has_erase(" " w " ")
    }
    function gather(s,   n, k, f, parts) {
      nt = 0
      n = split(s, parts, />>?[ \t]*/)
      for (k = 2; k <= n; k++) {
        if (match(parts[k], /^[^ \t;&|<>()]+/)) { f = substr(parts[k], 1, RLENGTH); gsub(/["\047\\]/, "", f); if (f != "") tfs[++nt] = f }
      }
      n = split(s, parts, /tee[ \t]+(-a[ \t]+)?/)
      for (k = 2; k <= n; k++) {
        if (match(parts[k], /^[^ \t;&|<>()]+/)) { f = substr(parts[k], 1, RLENGTH); gsub(/["\047\\]/, "", f); if (f != "") tfs[++nt] = f }
      }
    }
    function addfile(f,   b) {
      files[f] = 1
      b = f
      sub(/^.*\//, "", b)
      if (b != "") files[b] = 1
    }
    function scan(text,   n, k, seg, own, m) {
      text = redir(text)
      if (index(text, "jlink") == 0 && index(text, "erase") == 0) return
      n = split(text, segs, /[;&]+/)
      for (k = 1; k <= n; k++) {
        seg = segs[k]
        gather(seg)
        if (nt > 0 && seg ~ /(^|[ \t({|])(echo|printf)[ \t]/ && has_erase(seg)) {
          for (m = 1; m <= nt; m++) addfile(tfs[m])
        }
        if (index(seg, "jlink")) {
          own = seg
          gsub(/>>?[ \t]*[^ \t;&|<>()]+/, " ", own)
          gsub(/tee[ \t]+(-a[ \t]+)?[^ \t;&|<>()]+/, " ", own)
          if (index(own, "jlink")) jl[++nj] = own
        }
      }
    }
    function finish(   k) {
      if (body_erase) {
        if (feeds) hit = 1
        for (k = 1; k <= nt; k++) addfile(tfs[k])
        if (piped) pend = 1
      }
      inbody = 0
    }
    {
      line = $0
      if (inbody) {
        t = line
        if (delim != "") {
          if (dash) sub(/^\t+/, "", t)
          if (t == delim) { finish(); next }
        }
        if (has_erase(line)) body_erase = 1
        next
      }
      if (pend) { pend = 0; if (index(line, "jlink")) hit = 1 }
      scan(line)
      p = index(line, "<<")
      if (!p) next
      feeds = (line ~ /jlink(exe|\.exe)?[^|;&]*<</ || line ~ /<<.*\|&?[^;&]*jlink/)
      rest = substr(line, p + 2)
      if (substr(rest, 1, 1) == "<") {
        hs = substr(rest, 2)
        if (feeds) { if (has_erase(hs)) hit = 1 }
        else if (hs_erase(hs)) {
          l2 = redir(line)
          q = index(l2, "<<<")
          before = substr(l2, 1, q - 1)
          sub(/^.*[;&|(]/, "", before)
          after = substr(l2, q + 3)
          sub(/[;&].*$/, "", after)
          gather(before "<<<" after)
          for (k = 1; k <= nt; k++) addfile(tfs[k])
        }
        next
      }
      gather(line)
      piped = (line ~ /\|&?[ \t\r]*\\?[ \t\r]*$/)
      dash = (substr(rest, 1, 1) == "-")
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
      for (k = 1; k <= nj && !hit; k++) {
        n = split(jl[k], toks, /[ \t\r"\047=<>@(),:;&|]+/)
        for (m = 1; m <= n; m++) {
          if (toks[m] == "") continue
          if (toks[m] in files) { hit = 1; break }
          b = toks[m]
          sub(/^.*\//, "", b)
          if (b != "" && b in files) { hit = 1; break }
        }
      }
      print hit ? "hit" : "none"
    }
  ' <<<"$1"
}
if [ "$hit" -eq 0 ]; then
  # plain_ns has lost the backslash in `erase\>file`, where the > is an argument and no redirect, so
  # the second view marks an escaped < or > before normalising and the marker stops the word there.
  plain_jl="$(printf '%s\n' "$lower" | sed -E 's/[\][\]/'"$esc_pair"'/g; s/[\]([<>])/'"$esc_mark"'\1/g; s/'"$esc_pair"'/\\\\/g' | normalise)"
  for source in "$lower" "$plain_jl"; do
    heredoc="$(jl_scan "$source")" || heredoc="failed"
    # The awk prints hit or none; no answer means it did not run (the here-string failed to write).
    case "$heredoc" in
      hit)
        hit=1
        break
        ;;
      none) ;;
      *)
        echo "blocked: could not scan the command for a J-Link heredoc (awk gave no answer), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
        exit 2
        ;;
    esac
  done
fi
if [ "$hit" -eq 1 ]; then
  echo "blocked: whole-device erase or readout-protection write. Dump flash and option bytes first (for example 'st-flash read dump.bin 0x08000000 <size>' or 'nrfjprog --readcode dump.hex'), keep the dump, then ask for the erase explicitly." >&2
  exit 2
fi
if [ "$hit" -eq 3 ]; then
  echo "blocked: openocd 'flash erase_address' erases a range, and this hook cannot compare the range with the size of the chip, so it cannot tell a sector from the whole device. Dump flash first (for example 'openocd -c \"flash read_bank 0 dump.bin\"'), keep the dump, erase by sector with 'flash erase_sector', or ask for the erase explicitly." >&2
  exit 2
fi
exit 0
