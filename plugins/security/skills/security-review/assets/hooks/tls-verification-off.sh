#!/usr/bin/env bash
# Report a written config file that switches off TLS certificate verification. A committed
# skip reaches every environment that reads the file and outlives the reason for it, while the
# fix (trust the right CA) is usually a few lines. Deterministic: standard tools only, no
# network, no secrets, nothing run from the file.
#
# What it checks. For a written file whose path ends in .yaml, .yml, .json, .toml, .ini or
# .conf, the file is read from disk at tool_input.file_path, so an Edit is judged on the whole
# file and not on its fragment. A line that is not a comment (first non-blank character "#",
# ";" or "//") and that sets one of insecure-skip-tls-verify, insecure-skip-verify,
# skip-tls-verify or tls-skip-verify to true, yes, on or 1, or one of validate_certs,
# verify_ssl, ssl_verify, strict-ssl or rejectunauthorized to false, no, off or 0, is a
# finding. The words may be joined by a dash, an underscore or nothing, and case is ignored,
# so insecureSkipVerify, tlsSkipVerify, sslverify (yum, git) and rejectUnauthorized (Node)
# are read too. A value may be quoted. The hook exits 2 and prints path:line and a fixed message for up to ten findings,
# never text from the file. A line carrying the word "tls-exception" is allowed: that is how a recorded exception says so.
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the
#     model, which can fix the file; the hook cannot undo anything.
#   - Config files only. A skip written in code (Python verify=False, JavaScript
#     rejectUnauthorized in a JavaScript call, a Go client option), a command-line flag, GIT_SSL_NO_VERIFY, or an
#     extensionless client config file is not seen. Terraform (.tf) is left out on purpose.
#   - A bare "verify: false" or "insecure: true" is not matched: the key names no TLS, and it
#     would flag every unrelated setting that carries those words. Look for them in review.
#   - A line is read alone: a key and its value on different lines, a value built from a
#     variable or template, or a multi-line YAML scalar is not seen. A "#" comment after a
#     value does not hide it, but a key inside a multi-line string counts.
#   - The "tls-exception" marker is a convention the reader can see in review, not proof that
#     an exception was granted. JSON cannot carry a comment, so a recorded JSON exception has
#     to put the marker in a string value on the same line.
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

case "$file" in
  *.yaml | *.yml | *.json | *.toml | *.ini | *.conf) ;;
  *) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check TLS verification in the file yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to check TLS verification. Check the file is readable, then retry." >&2
  exit 2
fi
# No real config file is near this size. The scan below is linear, so the limit bounds the
# work; a hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. A config file is far smaller; check what was written to it." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file. A cheap
# pre-filter: a file that never names a verification key has nothing to judge.
rc=0
grep -qi -e 'skip.*verify' -e 'validate.*certs' -e 'verify.*ssl' -e 'ssl.*verify' \
  -e 'strict.*ssl' -e 'reject.*unauthorized' <"$file" || rc=$?
case "$rc" in
  0) ;;
  1) exit 0 ;;
  *)
    echo "blocked: could not read $file to check TLS verification. Check the file is readable, then retry." >&2
    exit 2
    ;;
esac

# One awk pass. Each line is lowercased once and tested by a single regular expression, so the
# work is linear in the line length: a key at a word boundary, an optional quote, ":" or "=",
# an optional quote, the bad value and a non-word character or the end. A comment line and a
# line with the exception marker are skipped before that. awk prints a last line, @@done, so
# that an awk that did not run (killed, or the redirection failed) is told from one that
# found nothing wrong.
rc=0
verdict="$(
  awk '
    {
      l = tolower($0)
      if (l ~ /^[ \t]*(#|;|\/\/)/) next
      if (index(l, "tls-exception") > 0) next
      if (l ~ /(^|[^a-z0-9_-])(((insecure[-_]?skip[-_]?tls[-_]?verify|insecure[-_]?skip[-_]?verify|skip[-_]?tls[-_]?verify|tls[-_]?skip[-_]?verify)["\047]?[ \t]*[:=][ \t]*["\047]?(true|yes|on|1))|((validate[-_]?certs|verify[-_]?ssl|ssl[-_]?verify|strict[-_]?ssl|reject[-_]?unauthorized)["\047]?[ \t]*[:=][ \t]*["\047]?(false|no|off|0)))([^a-z0-9_]|$)/) {
        n++
        if (n <= 10) printf "%d:TLS verification is switched off here\n", NR
      }
    }
    END { print "@@done" }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for disabled TLS verification (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
finding="${verdict%@@done}"
finding="${finding%$'\n'}"

if [ -n "$finding" ]; then
  {
    echo "blocked: $file turns off TLS certificate verification. The write already happened; revert it now."
    while IFS= read -r line; do
      printf '%s:%s\n' "$file" "$line"
    done <<<"$finding"
    echo "Trust the issuing CA instead (add it to the client's CA bundle). A recorded, time-boxed exception goes in tls-verification-exception.md and its id goes on the line as tls-exception."
  } >&2
  exit 2
fi
exit 0
