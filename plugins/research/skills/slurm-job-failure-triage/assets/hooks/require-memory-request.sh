#!/usr/bin/env bash
# Report a written Slurm batch script that has #SBATCH directives and none that asks for
# memory. A job with no memory request gets the site default, a number nobody chose, and an
# OUT_OF_MEMORY kill against it cannot be judged afterwards. Deterministic: standard tools
# only, no network, no secrets, nothing run from the file.
#
# What it checks. For a written file whose path ends in .sbatch or has a slurm directory
# above a .sh file, the file is read from disk at tool_input.file_path, so an Edit is judged
# on the whole file and not on its fragment. A line starting "#SBATCH" and a space or tab is
# a directive. If the file has at least one directive and none carries --mem, --mem-per-cpu
# or --mem-per-gpu (followed by "=", a space or a tab), the hook exits 2 and names the file
# and the line of the first directive. A file with no directive, or another path, is allowed.
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the
#     model, which can fix the file; the hook cannot undo anything.
#   - Memory requested somewhere else is invisible: on the sbatch command line, in an
#     SBATCH_* environment variable, or by --exclusive on a site that gives a whole node.
#     Such a script gets a finding that is safe to ignore.
#   - A directive is read as one line. A "--mem" in a trailing comment on a directive, or in
#     a quoted string or heredoc, counts as a request. A directive indented before "#SBATCH"
#     or a continuation line is not read as a directive.
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

# **/*.sbatch and **/slurm/**/*.sh. The slash on both sides of "slurm" keeps a directory such
# as myslurm/ out.
case "$file" in
  *.sbatch | */slurm/*.sh | slurm/*.sh) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the memory request yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to check it for a memory request. Check the file is readable, then retry." >&2
  exit 2
fi
# No real batch script is near this size. The scan below is linear, so the limit bounds the
# work; a hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. A batch script is far smaller; check what was written to it." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; only the
# first two are an answer. A file with no directive has nothing to judge.
rc=0
grep -q '^#SBATCH' <"$file" || rc=$?
case "$rc" in
  0) ;;
  1) exit 0 ;;
  *)
    echo "blocked: could not read $file to check it for a memory request. Check the file is readable, then retry." >&2
    exit 2
    ;;
esac

# One awk pass, no backtracking: a prefix compare per line, then a single unanchored match.
# The line gets a trailing space so that "--mem" at the very end still ends in a separator,
# which spares an end-of-line anchor. awk prints a last line, @@done, so that an awk that did
# not run (killed, or the redirection failed) is told from one that found nothing wrong.
# On a finding it prints the line number and the first 120 bytes of the first directive.
rc=0
verdict="$(
  awk '
    substr($0, 1, 7) == "#SBATCH" {
      c = substr($0, 8, 1)
      if (c != " " && c != "\t") next
      if (!first) { first = NR; text = substr($0, 1, 120) }
      if (!found) {
        line = $0 " "
        if (match(line, /--mem(-per-cpu|-per-gpu)?[= \t]/)) found = 1
      }
    }
    END {
      if (first && !found) printf "%d:%s\n", first, text
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for a memory request (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
finding="${verdict%@@done}"
finding="${finding%$'\n'}"

if [ -n "$finding" ]; then
  {
    echo "blocked: $file has #SBATCH directives and none asks for memory, so the job gets the site default and an OUT_OF_MEMORY kill cannot be judged against a request. The write already happened; add a request now."
    printf '%s:%s\n' "$file" "$finding"
    echo "Add one of: #SBATCH --mem=4G, #SBATCH --mem-per-cpu=2G or #SBATCH --mem-per-gpu=16G. If memory is set at submission, on the sbatch command line, this finding can be ignored."
  } >&2
  exit 2
fi
exit 0
