#!/usr/bin/env bash
# Report a written sysctl file that sets a removed or unexplained network ceiling.
#
# What it checks: in a file named sysctl.conf or *.conf under a sysctl.d directory, (1) any
# line that sets net.ipv4.tcp_tw_recycle, which broke clients behind NAT and was removed in
# Linux 4.12, and (2) any line that sets net.netfilter.nf_conntrack_max, net.nf_conntrack_max,
# net.ipv4.netfilter.ip_conntrack_max or net.ipv4.ip_local_port_range with no comment directly
# above it that holds a digit. The digit stands for a recorded value: the counter at failure
# or the limit it hit. A key may be written with dots or slashes and with a leading "-".
# Comment lines (# or ;) and blank lines are skipped; a blank line ends the comment block.
#
# The check reads the WRITTEN FILE from disk at tool_input.file_path, because an Edit carries
# only a fragment. It does not read the command text and parses no shell. Exit 2 puts file:line
# findings on stderr; exit 0 allows. A file over 1 MiB is refused unread.
#
# Known limits: PostToolUse runs after the write, so exit 2 only feeds the message back to the
# model, which can fix the file but cannot undo the write. The whole file is judged, so an
# older line that already breaks the rule is reported on every later edit. A digit in the
# comment is a proxy for evidence, not proof of it. Values are not judged, so a ceiling lowered
# or set to the kernel default still needs its comment. Settings made by other means (sysctl -w,
# a Kubernetes securityContext, kube-proxy flags) are not seen. Standard tools only, no
# network, no secrets.
set -Eeuo pipefail

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

# Only a sysctl file. Anything else, and no path at all, is not judged.
case "$file" in
  sysctl.conf | */sysctl.conf | sysctl.d/*.conf | */sysctl.d/*.conf) ;;
  *) exit 0 ;;
esac
# A file that is not there (a deleted file, a path from another machine) has nothing to judge.
[ -f "$file" ] || exit 0

# From here on the hook has something to judge, so a missing tool is a refusal and not a pass:
# letting the write through unchecked would make the hook look like it ran.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the sysctl lines yourself." >&2
    exit 2
  fi
done
export LC_ALL=C

# No real sysctl file is near 1 MiB. Refusing bounds the work and keeps the hook inside its
# timeout, because a hook that outlasts it fails open.
size="$(wc -c <"$file")" || size=""
case "$size" in
  '' | *[!0-9' ']*)
    echo "blocked: could not measure $file, so it was not judged. Retry; if it repeats, check the file's permissions." >&2
    exit 2
    ;;
esac
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not judge. Split the file, or check its sysctl lines yourself." >&2
  exit 2
fi

# Cheap screen: a file that names none of the keys has nothing to report. grep -c prints a
# count even for no match, so no count means grep did not run; only status 0 with a count or
# status 1 with a count of 0 is an answer.
rc=0
count="$(grep -c -E 'tcp_tw_recycle|nf_conntrack_max|ip_conntrack_max|ip_local_port_range' <"$file")" || rc=$?
case "$rc:$count" in
  0:[1-9]*) ;;
  1:0) exit 0 ;;
  *)
    echo "blocked: could not scan $file with grep (status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
    exit 2
    ;;
esac

# One awk pass, linear in the file: every pattern is anchored at the start of a line and no
# regex is run against the end of a long input. awk prints a last line, @@done, so an awk that
# did not run to the end (killed, or out of space) is told from one that found nothing.
# State across lines: `note` is 1 when the comment block directly above holds a digit.
rc=0
verdict="$(
  HOOK_FILE="$file" awk '
    function show(n, why, text) {
      found++
      if (found <= 20) printf "%s:%d: %s: %s\n", ENVIRON["HOOK_FILE"], n, why, substr(text, 1, 200)
    }
    {
      line = $0
      n = length(line)
      if (substr(line, n, 1) == "\r") line = substr(line, 1, n - 1)
      text = line
      sub(/^[ \t]+/, "", text)
      first = substr(text, 1, 1)
      if (first == "#" || first == ";") {
        if (text ~ /[0-9]/) note = 1
        next
      }
      if (text == "") {
        note = 0
        next
      }
      if (text ~ /^-?net[.\/]ipv4[.\/]tcp_tw_recycle[ \t]*=/) {
        show(NR, "tcp_tw_recycle was removed in Linux 4.12", line)
      } else if (text ~ /^-?net[.\/](netfilter[.\/])?nf_conntrack_max[ \t]*=/ || text ~ /^-?net[.\/]ipv4[.\/]netfilter[.\/]ip_conntrack_max[ \t]*=/ || text ~ /^-?net[.\/]ipv4[.\/]ip_local_port_range[ \t]*=/) {
        if (!note) show(NR, "no evidence comment above", line)
      }
      note = 0
    }
    END {
      if (found > 20) printf "... and %d more\n", found - 20
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for network ceilings (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
found="${verdict%@@done}"
found="${found%$'\n'}"

if [ -n "$found" ]; then
  {
    echo "blocked: a sysctl file sets a network ceiling the connection-exhaustion-hunt skill does not allow."
    echo "Drop net.ipv4.tcp_tw_recycle; for a conntrack or port-range ceiling, put a comment directly above"
    echo "it with the counter, its value at failure and the limit it hit (a Kubernetes node's"
    echo "nf_conntrack_max is also reset by kube-proxy, so change its settings instead):"
    printf '%s\n' "$found"
  } >&2
  exit 2
fi
exit 0
