#!/usr/bin/env bash
# Report a written OpenTelemetry collector configuration whose pipeline lists processors but
# no memory_limiter. Deterministic: standard tools only, no network, no secrets, no eval.
#
# What it checks: for a file named otel-collector*.yml or .yaml, or any .yml or .yaml under a
# directory whose name starts with otel or otelcol, it reads the file from disk (an Edit only
# carries a fragment, so the written file is the thing to judge) and finds the service
# pipelines: key. Each pipeline under it whose processors: list is non-empty must name
# memory_limiter (or memory_limiter/<name>) in that list. A pipeline with no processors, or
# a file with no pipelines: key, is allowed. Findings go to stderr as file:line.
#
# Known limits: it reads block-style YAML, with the processors list either as "- item" lines
# or as a [flow, list] on one or more lines. It does not read a pipelines: map written in flow
# style, YAML anchors and aliases, a list supplied by a template, or a limiter defined in a
# second file merged with --config, so a config split across files can be reported falsely
# and a pipeline built through an alias can pass. It does not check the limiter's position or
# its limits; the otel-collector-pipeline-review skill does. Comments are cut at a space
# before "#", so a quoted "#" in a value is misread.
#
# This is a PostToolUse hook: the write has already happened. Exit 2 only feeds the findings
# back to the model, which can correct the file; nothing is undone. A file over 1 MiB is
# refused, not scanned, with exit 2.
set -Eeuo pipefail
export LC_ALL=C

input="$(cat)"
file=""
# Either parser prints nothing, and the hook allows, for input it cannot read a path from:
# invalid JSON, a non-object, a missing tool_input, or a non-string file_path.
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

# The rule's two globs. In a case pattern * also matches a slash, which is what ** means here.
case "$file" in
  otel-collector*.yml | otel-collector*.yaml | */otel-collector*.yml | */otel-collector*.yaml) ;;
  otel*/*.yml | otel*/*.yaml | */otel*/*.yml | */otel*/*.yaml) ;;
  *) exit 0 ;;
esac

# A path that matches is judged, so a tool this hook needs and cannot find is a refusal, not
# an allow: letting the write through unjudged is the failure the hook exists to prevent.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the collector configuration yourself." >&2
    exit 2
  fi
done

[ -f "$file" ] || exit 0

# No real collector configuration is near 1 MiB. The limit bounds the work and keeps the hook
# inside its timeout, past which it fails open.
if ! size="$(wc -c <"$file" 2>/dev/null)"; then
  echo "blocked: could not read $file to check it for a memory_limiter. Check the file is readable, then retry." >&2
  exit 2
fi
size="${size//[[:space:]]/}"
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. Split the collector configuration, or check it for a memory_limiter yourself." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; -c prints a
# count either way, so no count means grep did not run. Only those two outcomes are an answer.
rc=0
count="$(grep -c -F -e 'pipelines:' -- "$file")" || rc=$?
case "$rc:$count" in
  0:[1-9]*) ;;
  1:0) exit 0 ;;
  *)
    echo "blocked: could not scan $file with grep (status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
    exit 2
    ;;
esac

# One awk pass, every regex anchored at the start of the line or searching forward only, so
# the cost is linear in the file. A pipeline is the block under pipelines: at the indent of
# its first child; it ends at the next line at that indent or less. awk prints a last line,
# @@done, so an awk that did not run to the end is told from one that found nothing.
rc=0
verdict="$(
  FILE_PATH="$file" awk '
    function flush() {
      if (inpipe && hasproc && !hasmem) {
        printf "%s:%d: pipeline %s lists processors but no memory_limiter\n", ENVIRON["FILE_PATH"], procline, pname
      }
      inpipe = 0; hasproc = 0; hasmem = 0; mode = ""
    }
    {
      line = $0
      if (length(line) > 0 && substr(line, length(line), 1) == "\r") line = substr(line, 1, length(line) - 1)
      sub(/(^|[ \t])#.*/, "", line)
      match(line, /^[ \t]*/)
      ind = RLENGTH
      if (ind == length(line)) next
      body = substr(line, ind + 1)

      if (inblock && ind <= pind) { flush(); inblock = 0 }

      if (!inblock) {
        if (substr(body, 1, 10) == "pipelines:") {
          rest = substr(body, 11)
          match(rest, /^[ \t]*/)
          if (RLENGTH == length(rest)) { inblock = 1; pind = ind; cind = -1 }
        }
        next
      }

      if (cind < 0) cind = ind
      if (ind <= cind) {
        flush()
        cind = ind
        inpipe = 1
        colon = index(body, ":")
        pname = colon ? substr(body, 1, colon - 1) : body
        procline = NR
        next
      }

      if (substr(body, 1, 11) == "processors:") {
        mode = ""
        procind = ind
        procline = NR
        rest = substr(body, 12)
        match(rest, /^[ \t]*/)
        rest = substr(rest, RLENGTH + 1)
        if (rest == "") {
          mode = "block"
        } else if (substr(rest, 1, 1) == "[") {
          if (index(rest, "memory_limiter")) hasmem = 1
          if (rest !~ /^\[[ \t]*\]/) hasproc = 1
          if (!index(rest, "]")) mode = "flow"
        }
        next
      }

      if (mode == "block") {
        if (substr(body, 1, 1) == "-") {
          hasproc = 1
          if (index(body, "memory_limiter")) hasmem = 1
        } else if (ind <= procind) {
          mode = ""
        }
      } else if (mode == "flow") {
        if (index(body, "memory_limiter")) hasmem = 1
        if (index(body, "]")) mode = ""
      }
    }
    END { flush(); print "@@done" }
  ' <"$file"
)" || rc=$?
if [ "$rc" -eq 127 ]; then
  echo "blocked: awk is not installed, so this hook cannot read $file and did not judge it. Install awk (any POSIX awk), or check the collector configuration yourself." >&2
  exit 2
fi
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for a memory_limiter (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
found="${verdict%@@done}"
found="${found%$'\n'}"

if [ -n "$found" ]; then
  {
    echo "blocked: a collector pipeline lists processors but no memory_limiter, so under load the kernel kills the collector instead of the pipeline refusing data. The write already happened; add memory_limiter as the first processor of each pipeline named below:"
    printf '%s\n' "$found"
  } >&2
  exit 2
fi
exit 0
