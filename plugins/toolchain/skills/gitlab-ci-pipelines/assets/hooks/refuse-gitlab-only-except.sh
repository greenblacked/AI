#!/usr/bin/env bash
# Refuse a write whose new content contains an only: or except: key line, in a GitLab CI file.
# It judges the text it is given, not the diff: a Write of a legacy file, or an Edit whose new
# text keeps an existing only: line, is refused too. It misses flow maps (job: {only: [main]}) and refuses an only: line inside a block scalar,
# since it does not parse YAML.
# Scope: Write, Edit and MultiEdit to a file named .gitlab-ci.yml, ending in .gitlab-ci.yml, or
# under .gitlab/ci/ and ending in .yml or .yaml. It reads the new content (content, new_string, or each edits[].new_string)
# and nothing on disk. Any other file, and input it cannot read, is allowed: a hook that blocks
# on a payload it cannot parse reports a failure over a write it never judged.
# Deterministic: standard tools only, no network, no secrets.
set -Eeuo pipefail

input="$(cat)"
path=""
text=""
if command -v jq >/dev/null 2>&1; then
  path="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" and (.tool_input.file_path|type)=="string" then .tool_input.file_path else empty end' \
    2>/dev/null || true)"
  text="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then
       .tool_input as $t
       | [($t.content, $t.new_string), (($t.edits // [])[]? | .new_string?)]
       | map(select(type=="string")) | join("\n")
     else empty end' 2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  parsed="$(printf '%s' "$input" | python3 -I -c \
    'import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
if not isinstance(tool, dict):
    sys.exit(0)
path = tool.get("file_path")
parts = [tool.get("content"), tool.get("new_string")]
edits = tool.get("edits")
if isinstance(edits, list):
    parts += [e.get("new_string") for e in edits if isinstance(e, dict)]
text = "\n".join(p for p in parts if isinstance(p, str))
if not text or not isinstance(path, str) or "\n" in path:
    sys.exit(0)
print(path)
print(text)' || true)"
  path="${parsed%%$'\n'*}"
  text="${parsed#*$'\n'}"
fi

[ -n "$path" ] || exit 0
# A path with a newline cannot round-trip through the fallback's line split; jq allows it too.
case "$path" in *$'\n'*) exit 0 ;; esac
[ -n "$text" ] || exit 0

base="${path##*/}"
is_ci=0
case "$base" in
  .gitlab-ci.yml | *.gitlab-ci.yml) is_ci=1 ;;
esac
case "$path" in
  .gitlab/ci/*.yml | */.gitlab/ci/*.yml | .gitlab/ci/*.yaml | */.gitlab/ci/*.yaml) is_ci=1 ;;
esac
[ "$is_ci" -eq 1 ] || exit 0

# grep -c prints a count even with no match; a failed run prints nothing, which is not an answer.
rc=0
count="$(grep -Ec '^[[:space:]]*["'"'"']?(only|except)["'"'"']?[[:space:]]*:' <<<"$text")" || rc=$?
case "$rc:$count" in
  0:[1-9]*)
    echo "blocked: $path contains only: or except:. Use rules: instead (they cannot be mixed in one job and their refs behave differently in merge request pipelines), with workflow:rules deciding which pipelines exist." >&2
    exit 2
    ;;
  1:0) exit 0 ;;
esac
echo "blocked: could not scan the new content with grep (status $rc), so it was not judged. Retry." >&2
exit 2
