#!/usr/bin/env bash
# Refuse a command that drops or truncates a warehouse object. Deterministic: standard tools
# only, no network, no secrets. One text match, not a SQL parser: DDL written to a file and run
# later passes, and a prose mention in the command also blocks, which is the safe direction.
# It does not replace db-migration, which governs application-database schema changes.
# It reads the command text and nothing else. It undoes quoting, backslashes and line continuations
# before matching, and refuses a command that names a SQL client or a DROP or TRUNCATE in a spelling
# it cannot read ($'..' escapes, brace expansion, a variable or substitution as the command, which is read right after a separator or after
# sudo, exec, command and similar wrappers, not after other wrappers) rather
# than guessing.
# SQL comments are not parsed: dialects disagree on nesting, on executable comments (/*! */, /*M! */),
# and on --, // and #, so no text match reads them all. Instead the hook fails closed: a command that
# has DROP (with a table, view, schema, database or column word anywhere in it) or TRUNCATE (followed
# by an identifier) as a word, or `bq` with `rm`, and also any marker (/*, */, --, #, //, $ or a
# backtick) is refused, with a request to write the statement without comments. `--` counts, so
# `truncate --size 0 f` is refused while `truncate -s 0 f` passes; that cost is accepted. It also
# refuses a harmless `truncate -s 0 f # x` and a prose mention in a comment, which is the safe direction. A .sql or script file the command
# runs is out of scope: the hook cannot see what is in it.
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
# missing tool is worse than none.
if [ -z "$command" ]; then
  if ! command -v jq >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
    echo "block-destructive-warehouse-ddl: neither jq nor python3 found, allowing" >&2
  fi
  exit 0
fi

# Byte-wise matching (LC_ALL=C): under a UTF-8 locale GNU grep takes quadratic time on the patterns
# below for a command with a long run of spaces or letters, so a large command outlasts the hook
# timeout, and a timed-out hook fails open. Upper case is only folded for ASCII, which is all a
# keyword uses; a byte outside ASCII (not a tab or other control byte) counts as an identifier start
# in truncate_re, as a letter did.
export LC_ALL=C
# Word-bounded and SQL-shaped, so "truncated" and `truncate -s 0 file` pass while
# `TRUNCATE TABLE t`, `truncate t`, `DROP MATERIALIZED VIEW v`, `DROP SNAPSHOT TABLE t` and
# `DROP DYNAMIC TABLE t` block.
drop_re='\<drop[[:space:]]+((external|materialized|snapshot|dynamic|temp|temporary)[[:space:]]+)?(table|view|schema|database|column)\>'
truncate_re='\<truncate[[:space:]]+(table[[:space:]]+)?([[:alpha:]_"`[\\]|[^[:print:][:cntrl:]])'
bq_re='\<bq[[:space:]]+rm\>'
# A text match cannot read the shell's own spellings, so the command is normalised first: a
# backslash-newline continuation is joined, the $ of $'..' and $".." is dropped, and quotes and
# backslashes are deleted, which makes DR\OP\ TABLE\ t and "DR""OP TABLE t" the statement they
# spell. The patterns run on the command as written and on the normalised one, because a quoted
# identifier (truncate "t") is part of what truncate_re reads. Newlines stay in plain (a command
# word can start a line); plain_flat turns them into spaces. What cannot be normalised is refused
# instead, when the command also names a SQL client or a DDL word: a $'..' string with a backslash
# (hex and octal escapes), a brace expansion with a comma or `..` outside quotes (DROP{,} TABLE), and a
# variable, a command substitution or a backtick where the command word goes (right after a separator, a group opener, then, do or else, or one of the wrappers sudo, command, exec, xargs, nohup, time, busybox and builtin, with any NAME=value assignments between; a command run through another wrapper is not read) (c=psql; $c -c ...).
# A variable that is only the start of a path ($HOME/bin/psql) is read as the path it ends in.
# Indirection through a script file or a .sql file the client runs is out of scope: this hook sees
# only the command text.
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
  cmdpos='(^|[;&|`]|[$][(]|[[:space:]](then|do|else))[[:space:]]*([({][[:space:]]*)*((sudo|command|exec|xargs|nohup|time|busybox|builtin|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*)[[:space:]]+)*([$][A-Za-z_][A-Za-z0-9_]*([^/A-Za-z0-9_]|$)|[$]\{[^}]*\}([^/]|$)|[$][(0-9@*]|`)'
  hits "$(printf '%s' "$2" | tr '\n\r' ';;')" -E "$cmdpos"
}
# normalise needs awk. Without it the pipeline below fails with status 127, which is not a block,
# so the command would run unjudged; refuse instead, because a missing tool is not a reason to allow.
if [ -n "$command" ] && ! command -v awk >/dev/null 2>&1; then
  echo "blocked: awk is not installed, so this hook cannot read the command and did not judge it. Install awk (any POSIX awk), or run the command yourself." >&2
  exit 2
fi
plain="$(printf '%s\n' "$command" | normalise)"
plain_flat="$(printf '%s' "$plain" | tr '\n\r' '  ')"
client_re='(^|[^[:alnum:]_-])(psql|pgcli|mysql|mycli|mariadb|snowsql|bq|sqlcmd|sqlite3|duckdb|clickhouse-client|sqlplus|bteq|beeline|spark-sql|trino|presto|usql|databricks)([^[:alnum:]_-]|$)|drop|truncate'
if hits "$plain_flat" -iE "$client_re" && unreadable "$command" "$plain"; then
  echo "blocked: this hook could not read the command (a \$'...' escape, a brace expansion, or a variable or substitution where the command goes) and it names a SQL client or a DROP or TRUNCATE. Write the statement plainly so it can be seen whether it is destructive DDL." >&2
  exit 2
fi

# Newlines become spaces first, so a heredoc with DROP or TRUNCATE on one line and the object
# on the next is still one statement to the patterns.
flat="$(printf '%s' "$command" | tr '\n' ' ')"
# Fail closed on comments. The hook cannot read SQL comments reliably (nesting, MySQL and MariaDB
# executable comments, and which of --, // and # starts one differ by dialect), so a command with a
# destructive keyword and any comment marker is refused instead of guessed at. DROP needs an object
# word somewhere in the command, TRUNCATE a later identifier, as drop_re and truncate_re do, and
# `bq` needs `rm` as a word. The keyword patterns here have no left word boundary: a MySQL or
# MariaDB executable comment puts the keyword right after its version digits (/*!50100DROP TABLE t*/).
# A $ or a backtick counts as a marker too, because a variable or a substitution inside the SQL text
# can hide where a word ends or build the object word (DROP $e TABLE t, DROP $(printf T)ABLE t), so
# with one of those a DROP word alone is enough, without an object word beside it. Both the raw and the normalised text are read. A
# command without a marker is judged by the patterns below alone.
comment_re='/[*]|[*]/|--|#|//|[$]|`'
subst_re='[$]|`'
drop_word_re='drop\>'
drop_object_re='(table|view|schema|database|column)\>'
truncate_word_re='truncate\>.*(\<[[:alpha:]_]|["`[\\]|[^[:print:][:cntrl:]])'
comment_unreadable() {
  hits "$1" -Ei -e "$comment_re" || return 1
  { hits "$1" -Ei -e "$drop_word_re" && hits "$1" -Ei -e "$drop_object_re"; } ||
    hits "$1" -Ei -e "$truncate_word_re" ||
    { hits "$1" -Ei -e '\<bq\>' && hits "$1" -Ei -e '\<rm\>'; } ||
    { hits "$1" -Ei -e "$subst_re" && hits "$1" -Ei -e "$drop_word_re"; }
}
if comment_unreadable "$flat" || { [ "$plain_flat" != "$flat" ] && comment_unreadable "$plain_flat"; }; then
  echo "blocked: this hook cannot read SQL comments reliably, and the command has a comment marker (/*, */, --, #, //, $ or a backtick) beside a DROP, TRUNCATE or bq rm. Write the statement without comments." >&2
  exit 2
fi
if hits "$flat" -Ei -e "$drop_re" -e "$truncate_re" -e "$bq_re" ||
  { [ "$plain_flat" != "$flat" ] && hits "$plain_flat" -Ei -e "$drop_re" -e "$truncate_re" -e "$bq_re"; }; then
  echo "blocked: destructive warehouse DDL (DROP TABLE/VIEW/SCHEMA/DATABASE/COLUMN, TRUNCATE, bq rm). Rename the object, archive it, and run the drop yourself after the brownout." >&2
  exit 2
fi
exit 0
