#!/usr/bin/env bash
# Report a written .rs file in which a line opens an unsafe block, unsafe fn, unsafe impl or
# unsafe trait with no safety contract above it. Deterministic: standard tools only, no network,
# no secrets, nothing from the file is ever run.
#
# What it checks. The file is read from disk at tool_input.file_path, because an Edit carries
# only a fragment. A site needs a `// SAFETY:` comment on the same line or in the comment lines
# directly above it (blank lines and #[attributes] between are skipped). An unsafe fn or unsafe
# trait is also satisfied by a `# Safety` section in the doc comment above it.
#
# Known limits. It reads lines, not Rust: a multi-line block comment whose body lines do not
# start with `*`, a raw string, a `//` inside a char literal and a statement split over several
# lines (the comment must sit directly above the line that holds `unsafe`) can all be misread.
# `unsafe extern "C" { ... }` counts as a block; function pointer types and attributes such as
# `#[unsafe(no_mangle)]` do not count as sites. It does not judge whether the contract is any
# good, only that one is written.
#
# When it runs. This registers on PostToolUse, so the write has already happened: exit 2 feeds
# stderr back to the model, which can add the comment, and cannot undo the write.
set -Eeuo pipefail

input="$(cat)"
file=""
# Either parser prints nothing, and the hook allows, for input it cannot read a path from:
# invalid JSON, a non-object, a missing tool_input or a non-string file_path.
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

# Neither parser present, or nothing to judge: allow, because a hook that blocks everything on a
# missing tool is worse than no hook.
case "$file" in
  *.rs) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the hook must read the file. A missing tool is refused, not allowed: letting it
# through would turn an absent grep or awk into a silent pass. Checked up front so that the
# message is ours and not the shell's "command not found".
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or review the unsafe sites yourself." >&2
    exit 2
  fi
done

# Most .rs files hold no unsafe at all; one fixed-string pass settles those. The file is a
# redirection, never an argument, so a name starting with a dash cannot be read as an option.
# grep -c prints a count even for no match, so no count means grep did not run: only status 0
# with a count or status 1 with a count of 0 is an answer.
rc=0
count="$(LC_ALL=C grep -c -F -e unsafe <"$file")" || rc=$?
case "$rc:$count" in
  0:[1-9]*) ;;
  1:0) exit 0 ;;
  *)
    echo "blocked: could not scan $file with grep (status $rc), so it was not judged. Retry; if it repeats, check that the file is readable and the temporary directory has free space." >&2
    exit 2
    ;;
esac

# A file that holds unsafe and is larger than 1 MiB is refused rather than judged: no hand-written
# source is near that size, and a hook that outlasts its timeout fails open. The awk pass below
# is linear, so the limit bounds the work and does not guard a quadratic case.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size//[[:space:]]/}"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not measure $file (wc status $rc), so it was not judged. Retry." >&2
  exit 2
fi
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file holds unsafe code and is larger than 1 MiB, which this hook will not judge. Split the file, or review its unsafe sites with the rust-unsafe-review skill." >&2
  exit 2
fi

# One awk pass, byte-wise (LC_ALL=C). State is two flags: whether a SAFETY: comment and whether a
# "# Safety" doc heading has been seen since the last line of code. A blank line or an attribute
# keeps them; a comment line may set them; any other line is judged and then clears them.
# Lines without the word unsafe cost one index() call. For a line that has it, string literals
# are blanked, the trailing // comment is split off, and split() on the word finds each
# occurrence in one pass, so a long line is read once. Every regex is anchored at the start of a
# short slice, with no end anchor and no nested repeat, so none can backtrack over long input.
# awk prints a last line, @@done, so that an awk that did not run is told from one that found
# nothing wrong. The file name reaches awk through the environment, not -v, which would
# interpret backslashes in it.
rc=0
verdict="$(
  HOOK_FILE="$file" LC_ALL=C awk '
    {
      lead = $0
      sub(/^[ \t]+/, "", lead)
      if (lead == "") next
      two = substr(lead, 1, 2)
      if (two == "//" || two == "/*" || two == "* " || two == "*\t" || two == "*/" || lead == "*") {
        if (index(lead, "SAFETY:")) sc = 1
        if (index(lead, "# Safety")) sd = 1
        next
      }
      if (two == "#[" || two == "#!") next
      if (index(lead, "unsafe")) {
        s = lead
        gsub(/"[^"]*"/, "\"\"", s)
        cm = ""
        ci = index(s, "//")
        if (ci) {
          cm = substr(s, ci)
          s = substr(s, 1, ci - 1)
        }
        same = index(cm, "SAFETY:") ? 1 : 0
        n = split(s, p, "unsafe")
        kind = ""
        for (i = 2; i <= n && kind == ""; i++) {
          before = p[i - 1]
          if (before == "") {
            if (i > 2) continue
          } else if (substr(before, length(before), 1) ~ /[A-Za-z0-9_]/) continue
          first = substr(p[i], 1, 1)
          if (first != " " && first != "\t" && first != "{") continue
          t = substr(p[i], 1, 100)
          sub(/^[ \t]+/, "", t)
          if (substr(t, 1, 1) == "{") kind = "block"
          else if (t ~ /^extern[ \t]+(""[ \t]*)?\{/) kind = "block"
          else if (t ~ /^extern[ \t]+(""[ \t]+)?fn[ \t]+[A-Za-z_]/) kind = "fn"
          else if (t ~ /^fn[ \t]+[A-Za-z_]/) kind = "fn"
          else if (t ~ /^impl[ \t<]/) kind = "impl"
          else if (t ~ /^trait[ \t]/) kind = "trait"
        }
        if (kind != "") {
          ok = same || sc || ((kind == "fn" || kind == "trait") && sd)
          if (!ok) {
            bad++
            if (bad <= 50) printf "%s:%d: unsafe %s without a safety contract: %s\n", ENVIRON["HOOK_FILE"], NR, kind, substr(lead, 1, 100)
          }
        }
      }
      sc = 0
      sd = 0
    }
    END {
      if (bad > 50) printf "... and %d more\n", bad - 50
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for unsafe sites (awk status $rc), so it was not judged. Retry; if it repeats, check that the file is readable and the temporary directory has free space." >&2
  exit 2
fi
found="${verdict%@@done}"
found="${found%$'\n'}"

if [ -n "$found" ]; then
  {
    echo "blocked: an unsafe site needs a written contract. Put a // SAFETY: comment directly above it"
    echo "(an unsafe fn or unsafe trait may use a # Safety doc section instead), saying what it requires,"
    echo "who upholds that and why it holds here. The write already happened; add the comment now:"
    printf '%s\n' "$found"
  } >&2
  exit 2
fi
exit 0
