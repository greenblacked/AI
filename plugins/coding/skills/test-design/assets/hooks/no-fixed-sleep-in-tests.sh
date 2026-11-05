#!/usr/bin/env bash
# Report a written test file that waits with a fixed sleep. A fixed sleep is a race with a
# longer fuse: it slows every run by its whole length and still fails on a loaded runner.
# Deterministic: standard tools only, no network, no secrets, nothing run from the file.
#
# What it checks. For a written file whose path matches a test-file glob (*_test.go,
# test_*.py, *_test.py, *.test.ts, *.test.js, *.spec.ts, *Test.java, or a .py, .go, .java,
# .ts or .js file under a tests/ directory), the file is read from disk at
# tool_input.file_path, so an Edit is judged on the whole file and not on its fragment. A
# line that calls time.sleep(, time.Sleep(, Thread.sleep( or Thread.Sleep(, or has
# "await sleep(", is a finding unless its first non-blank text starts a comment ("#", "//",
# "/*" or "*") or the line contains "sleep-ok". The hook exits 2 and names up to five
# findings as path:line:text. Any other path, or a file with no such call, is allowed.
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the
#     model, which can fix the file; the hook cannot undo anything.
#   - Text matching cannot see a fake clock: a sleep on an injected clock that is meant to
#     advance, a sleep that is the behaviour under test (backoff, timeout, rate limit) and a
#     real child process or port wait are reported too. Mark those lines with "sleep-ok" and a
#     reason.
#   - Misses: "from time import sleep" then a bare sleep(1), setTimeout-based waits in
#     JavaScript, C# Thread.Sleep and any other spelling.
#   - A call after code on the same line is read, but a trailing comment or a string that
#     contains the call is read as the call itself. Block comments are only recognised on
#     lines that start with "/*" or "*".
#   - Only the file on disk after the write is judged, never a shell command that creates
#     one. A file over 1 MiB is refused, not scanned.
set -Eeuo pipefail
export LC_ALL=C

input="$(cat)"
file=""
# Either parser prints nothing, and the hook allows, for input it cannot read a path from:
# invalid JSON, a non-object, a missing tool_input or a path that is not a string.
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

# Neither parser present, or no path: allow, because a hook that blocks everything on a
# missing tool is worse than no hook.
[ -n "$file" ] || exit 0

# Test files by basename, so a directory called test_data/ is not read as a test file. Under a
# tests/ directory only source extensions are judged; a README there has nothing to sleep.
base="${file##*/}"
target=0
case "$base" in
  *_test.go | test_*.py | *_test.py | *.test.ts | *.test.js | *.spec.ts | *Test.java) target=1 ;;
esac
if [ "$target" -eq 0 ]; then
  case "$file" in
    */tests/* | tests/*)
      case "$base" in
        *.py | *.go | *.java | *.ts | *.js) target=1 ;;
      esac
      ;;
  esac
fi
[ "$target" -eq 1 ] || exit 0
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check for fixed sleeps yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to check it for fixed sleeps. Check the file is readable, then retry." >&2
  exit 2
fi
# No real test file is near this size. The scan below is linear, so the limit bounds the work;
# a hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. A test file is far smaller; check what was written to it." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; only the
# first two are an answer. A file that never says "leep" has nothing to judge.
rc=0
grep -q 'leep' <"$file" || rc=$?
case "$rc" in
  0) ;;
  1) exit 0 ;;
  *)
    echo "blocked: could not read $file to check it for fixed sleeps. Check the file is readable, then retry." >&2
    exit 2
    ;;
esac

# One awk pass, no backtracking: a comment-start match, then one alternation match per line.
# awk prints a last line, @@done, so that an awk that did not run (killed, or the redirection
# failed) is told from one that found nothing wrong. A finding is the line number and the first
# 120 bytes of the line; at most five are kept, and the total is counted past that.
rc=0
verdict="$(
  awk '
    index($0, "sleep-ok") { next }
    $0 ~ /^[ \t]*(#|\/\/|\/\*|\*)/ { next }
    $0 ~ /(time\.[sS]leep|Thread\.[sS]leep)\(|await[ \t]+sleep\(/ {
      total++
      if (total <= 5) printf "%d:%s\n", NR, substr($0, 1, 120)
    }
    END {
      if (total > 5) printf "...and %d more\n", total - 5
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for fixed sleeps (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
finding="${verdict%@@done}"
finding="${finding%$'\n'}"

if [ -n "$finding" ]; then
  {
    echo "blocked: $file waits with a fixed sleep, which slows every run and still fails on a loaded runner. The write already happened; replace the wait now."
    # Prefix each finding line with the path; a line without a number is the overflow note.
    printf '%s\n' "$finding" | while IFS= read -r line; do
      case "$line" in
        [0-9]*) printf '%s:%s\n' "$file" "$line" ;;
        *) printf '%s\n' "$line" ;;
      esac
    done
    echo "Wait on the condition instead: a latch, a barrier, a completion callback or a poll with a deadline, and inject the clock. If the sleep is the behaviour under test, add sleep-ok and the reason to that line."
  } >&2
  exit 2
fi
exit 0
