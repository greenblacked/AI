#!/usr/bin/env bash
# Require quoted evidence on every coded row of a churn coding sheet. Deterministic: standard
# tools only, no network, no secrets.
#
# Checks: a written CSV under a churn/ directory whose header holds both a "Primary code" and a
# "Key evidence" column (matched by content, case-insensitively, not by file name) must have a
# non-empty evidence cell on every row that has a primary code. A cell that is blank or holds only
# n/a, na, none, tbd, - or ? counts as empty. Findings are printed as file:line, where line is the
# line the row starts on.
#
# Known limits:
#   - It judges that evidence exists, not that it is good: a quote that does not support the code,
#     or a dropdown answer pasted into the evidence cell, passes. The dropdown rule is in
#     assets/rules/churn-coding.md.
#   - PostToolUse feedback comes after the write. Exit 2 hands stderr to the model, which can fix
#     the file; it cannot undo the write.
#   - The file is read from disk, so a sheet written by any other route is checked at its next
#     Write or Edit, not before. A path outside a churn/ directory, a name not ending in .csv, a
#     missing file and a CSV without both header names are allowed.
#   - Files over 1 MiB are refused, not judged. Only the first 200 columns are read for the
#     header; a delimiter other than a comma (a semicolon or tab export) is not understood. A
#     quoted field left open to the end of the file is reported, because rows after it cannot be
#     read.
#   - A header row is the first row that names both columns, so a title line above it is fine.
set -Eeuo pipefail

# One locale for every tool, so the byte-wise awk below behaves the same everywhere.
export LC_ALL=C

input="$(cat)"
file=""
# Either parser prints nothing, and the hook allows, for input it cannot read a path from:
# invalid JSON, a non-object, a missing tool_input, or a path that is not a string.
if command -v jq >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.file_path | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  file="$(printf '%s' "$input" | python3 -I -c \
    'import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
value = tool.get("file_path") if isinstance(tool, dict) else None
print(value if isinstance(value, str) else "")' || true)"
fi

# Neither parser present, or no path: allow, because a hook that blocks everything on a missing
# tool is worse than no hook.
[ -n "$file" ] || exit 0

case "$file" in
  */churn/*.csv | churn/*.csv) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here a file is to be judged, so a missing grep or awk refuses instead of letting it through.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked (after the write): $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX one), or check the sheet yourself." >&2
    exit 2
  fi
done

# No real coding sheet is near 1 MiB; refusing bounds the work, and a hook that outlasts its
# timeout fails open.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size//[[:space:]]/}"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked (after the write): could not read $file to check it for churn evidence. Check the file is readable, then retry." >&2
  exit 2
fi
if [ "$size" -gt 1048576 ]; then
  echo "blocked (after the write): $file is larger than 1 MiB, which this hook will not judge. Split the coding sheet into smaller files and check each." >&2
  exit 2
fi

# Cheap content test before the parse. grep exits 0 for a match, 1 for none and 2 or more when it
# could not read the file; only the first two are an answer.
primary=0
evidence=0
grep -qiF -- 'primary code' "$file" || primary=$?
grep -qiF -- 'key evidence' "$file" || evidence=$?
if [ "$primary" -gt 1 ] || [ "$evidence" -gt 1 ]; then
  echo "blocked (after the write): could not read $file to check it for churn evidence. Check the file is readable, then retry." >&2
  exit 2
fi
if [ "$primary" -eq 1 ] || [ "$evidence" -eq 1 ]; then
  exit 0
fi

# One awk pass reads the file as CSV: a double-quoted field may hold commas, doubled quotes and
# newlines, and a quote opens a field only at its start. Every loop is over the characters of a
# line once, and the text kept per field is capped at 80 bytes, so no string is rebuilt or
# rescanned from its end. The last line awk prints, @@done, tells an awk that finished from one that
# did not run.
rc=0
verdict="$(
  HOOK_FILE="$file" awk '
    function norm(s) {
      s = tolower(s)
      sub(/^[ \t\r]+/, "", s)
      sub(/[ \t\r]+$/, "", s)
      return s
    }
    function empty(s) {
      s = norm(s)
      return s == "n/a" || s == "na" || s == "none" || s == "tbd" || s == "-" || s == "?"
    }
    function endfield() {
      col++
      if (!hdr) {
        if (col <= 200) h[col] = txt
        if (col > hcols) hcols = col
      } else if (col == pc) {
        pcnb = nb
        pctxt = txt
      } else if (col == ke) {
        kenb = nb
        ketxt = txt
      }
      txt = ""; nb = 0; fstart = 1
    }
    function endrec(   j, a, b, t) {
      if (!hdr) {
        a = 0; b = 0
        for (j = 1; j <= hcols && j <= 200; j++) {
          t = norm(h[j])
          if (t == "primary code") a = j
          if (t == "key evidence") b = j
        }
        if (a && b) { hdr = 1; pc = a; ke = b }
        delete h
        hcols = 0
      } else if (pcnb && !empty(pctxt) && (!kenb || empty(ketxt))) {
        found++
        if (found <= 20) {
          shown = pctxt
          printf "%s:%d: primary code \"%s\" has no key evidence\n", ENVIRON["HOOK_FILE"], startline, shown
        }
      }
    }
    NR == 1 { sub(/^\357\273\277/, "") }
    {
      if (!inq) {
        startline = NR; col = 0; txt = ""; nb = 0; fstart = 1
        pcnb = 0; kenb = 0; pctxt = ""; ketxt = ""
      }
      n = length($0)
      for (i = 1; i <= n; i++) {
        c = substr($0, i, 1)
        if (inq) {
          if (c == "\"") {
            if (substr($0, i + 1, 1) == "\"") {
              i++
              nb = 1
              if (length(txt) < 80) txt = txt "\""
            } else {
              inq = 0
            }
          } else {
            if (c != " " && c != "\t" && c != "\r") nb = 1
            if (length(txt) < 80) txt = txt c
          }
        } else if (c == ",") {
          endfield()
        } else if (c == "\"" && fstart) {
          inq = 1
          fstart = 0
        } else {
          if (c != " " && c != "\t") fstart = 0
          if (c != " " && c != "\t" && c != "\r") nb = 1
          if (length(txt) < 80) txt = txt c
        }
      }
      if (!inq) {
        endfield()
        endrec()
      }
    }
    END {
      if (inq && hdr) {
        found++
        printf "%s:%d: a quoted field is never closed, so the rows after it were not checked\n", ENVIRON["HOOK_FILE"], startline
      }
      if (found > 20) printf "... and %d more\n", found - 20
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked (after the write): could not scan $file for churn evidence (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
missing="${verdict%@@done}"
missing="${missing%$'\n'}"

if [ -n "$missing" ]; then
  {
    echo "blocked (after the write): every coded churn reason needs quoted evidence. The write already happened; add a quoted line from the note or ticket, with its reference, to the Key evidence cell of each row below. The cancellation dropdown is not evidence."
    printf '%s\n' "$missing"
  } >&2
  exit 2
fi
exit 0
