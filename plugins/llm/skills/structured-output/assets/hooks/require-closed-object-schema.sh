#!/usr/bin/env bash
# Report an object schema written under schemas/ that does not close itself with
# "additionalProperties": false. Provider strict modes reject (Anthropic) or require
# (OpenAI) the closed form, and an open object lets the model invent fields that a
# validator then has to decide about. Deterministic: standard tools only, no network, no
# secrets, nothing from the file is ever run.
#
# What it checks. The tool call's file_path is matched against schemas/**/*.json. The file
# is then read from disk, not from the tool call, because an Edit carries only a fragment.
# It must parse as one JSON value and is walked as a JSON Schema: every subschema reached
# through properties, patternProperties, $defs, definitions, dependentSchemas, items,
# prefixItems, additionalItems, additionalProperties, not, if/then/else, contains,
# propertyNames, unevaluated*, allOf, anyOf and oneOf is a schema, and one whose "type" is
# or lists "object", or that holds a "properties" map, must have additionalProperties
# exactly false. A root with no type or properties is searched under "schema" and
# "input_schema" too, the envelope keys of the provider request bodies. Parsing uses jq
# when it is installed and python3 -I otherwise; both walk the same keywords.
#
# Known limits. It does not follow $ref, so a closed definition used through a $ref is
# judged where it is defined. enum, const, default and examples are not walked, so an
# object-shaped example is never flagged. A schema nested under other envelope keys
# (a function tool's "parameters", a response_format's "json_schema") is not found. A
# schema that is deliberately open (an input document, a free-form map) is flagged too;
# keep those outside schemas/ or accept the finding. Findings are JSON paths, because a
# parse has no line numbers. Without jq, python3 stops at about 1000 levels of nesting
# and the file is refused as too deep. A file over 1 MiB is refused, not scanned.
#
# When it runs. It is registered on PostToolUse, so the write has already happened: exit 2
# only feeds the findings back to the model, which can fix the file but cannot be undone by
# the hook. Exit 0 allows. With neither jq nor python3 it allows, because a hook that
# blocks everything on a missing tool is worse than none; with no grep or awk it refuses.
set -Eeuo pipefail
export LC_ALL=C

input="$(cat)"
file=""
# Either parser prints nothing, and the hook allows, for input it cannot read a path from:
# invalid JSON, a non-object payload, or a missing or non-object tool_input.
if command -v jq >/dev/null 2>&1; then
  mode=jq
  file="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.file_path | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  mode=python3
  file="$(printf '%s' "$input" | python3 -I -c \
    'import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
value = tool.get("file_path") if isinstance(tool, dict) else None
print(value if isinstance(value, str) else "")' || true)"
else
  exit 0
fi

# Only a JSON file under a schemas directory is judged. The glob is on the path as written,
# so a relative and an absolute path to the same file agree.
case "$file" in
  schemas/*.json | */schemas/*.json) ;;
  *) exit 0 ;;
esac
# A file that is gone, or is not a regular file, has nothing to read.
[ -f "$file" ] || exit 0

size="$(wc -c <"$file")" || size=""
size="${size//[[:space:]]/}"
case "$size" in
  '' | *[!0-9]*)
    echo "blocked: could not measure $file, so its schema was not checked. Retry; if it repeats, check that the file is readable." >&2
    exit 2
    ;;
esac
# No real schema is near 1 MiB. The walk is linear, so this bounds the work and keeps the
# hook inside its timeout, past which a hook fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. Split the schema into smaller files, or check it by hand." >&2
  exit 2
fi

# A missing grep or awk would exit 127, which is not a block, so the file would go unjudged.
for tool in grep awk; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read the findings and did not judge $file. Install $tool (any POSIX $tool), or check the schema yourself." >&2
    exit 2
  fi
done

# Prints one JSON path per object schema that is not closed. A path starts with a dollar sign.
# Status 3 from python3 is a file that is not one JSON value; 4 is nesting past its limit.
find_open_objects() {
  if [ "$mode" = jq ]; then
    jq -n -r '
      def esc: gsub("[\\x00-\\x1f\\x7f]"; "?");
      def isobj: (.type == "object")
        or ((.type | type) == "array" and any(.type[]; . == "object"))
        or ((.properties | type) == "object");
      def sub_schema($p):
        if type == "object" then
          (if isobj and (.additionalProperties != false) then $p else empty end),
          ( ("properties", "patternProperties", "$defs", "definitions", "dependentSchemas") as $k
            | (.[$k] | select(type == "object") | to_entries[])
            | (.key | esc) as $n
            | (.value | sub_schema($p + "." + $k + "." + $n)) ),
          ( ("items", "additionalProperties", "not", "if", "then", "else", "contains",
             "propertyNames", "unevaluatedItems", "unevaluatedProperties", "additionalItems") as $k
            | (.[$k] | select(type == "object" or type == "array")) as $v
            | if ($v | type) == "object" then ($v | sub_schema($p + "." + $k))
              else ($v | to_entries[] | (.key | tostring) as $i | (.value | sub_schema($p + "." + $k + "[" + $i + "]"))) end ),
          ( ("allOf", "anyOf", "oneOf", "prefixItems") as $k
            | (.[$k] | select(type == "array") | to_entries[])
            | (.key | tostring) as $i
            | (.value | sub_schema($p + "." + $k + "[" + $i + "]")) )
        else empty end;
      [inputs]
      | if length != 1 then error("expected one JSON value") else .[0] end
      | if type == "object" then
          ( sub_schema("$"),
            ( if isobj then empty else
                ("schema", "input_schema") as $k
                | (.[$k] | select(type == "object")) | sub_schema("$." + $k)
              end ) )
        else empty end' <"$file"
  else
    python3 -I -c '
import json, re, sys

sys.stdout.reconfigure(errors="replace")

MAPS = ("properties", "patternProperties", "$defs", "definitions", "dependentSchemas")
ONES = ("items", "additionalProperties", "not", "if", "then", "else", "contains",
        "propertyNames", "unevaluatedItems", "unevaluatedProperties", "additionalItems")
LISTS = ("allOf", "anyOf", "oneOf", "prefixItems")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def isobj(node):
    kind = node.get("type")
    return (
        kind == "object"
        or (isinstance(kind, list) and "object" in kind)
        or isinstance(node.get("properties"), dict)
    )


def walk(node, path):
    if not isinstance(node, dict):
        return
    if isobj(node) and node.get("additionalProperties") is not False:
        print(path)
    for key in MAPS:
        value = node.get(key)
        if isinstance(value, dict):
            for name, child in value.items():
                walk(child, path + "." + key + "." + CONTROL.sub("?", name))
    for key in ONES:
        value = node.get(key)
        if isinstance(value, dict):
            walk(value, path + "." + key)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, path + "." + key + "[" + str(i) + "]")
    for key in LISTS:
        value = node.get(key)
        if isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, path + "." + key + "[" + str(i) + "]")


try:
    root = json.loads(sys.stdin.buffer.read())
except RecursionError:
    sys.exit(4)
except ValueError:
    sys.exit(3)
try:
    if isinstance(root, dict):
        walk(root, "$")
        if not isobj(root):
            for key in ("schema", "input_schema"):
                if isinstance(root.get(key), dict):
                    walk(root[key], "$." + key)
except RecursionError:
    sys.exit(4)
' <"$file"
  fi
}

rc=0
found="$(find_open_objects 2>/dev/null)" || rc=$?
case "$rc" in
  0) ;;
  4)
    echo "blocked: $file is nested too deeply for this hook to walk, so its schema was not checked. Flatten it; a schema this deep is hard for a provider to compile too." >&2
    exit 2
    ;;
  *)
    echo "blocked: $file is not one valid JSON value (or is nested too deeply), so its schema was not checked. Fix the JSON, then write it again." >&2
    exit 2
    ;;
esac
[ -n "$found" ] || exit 0

# grep -c prints a count even for no match, so no count means grep did not run (a here-string
# that cannot be written fails the redirection before grep starts). Only a count is an answer.
grc=0
count="$(grep -c '^\$' <<<"$found")" || grc=$?
case "$grc:$count" in
  0:[1-9]*) ;;
  *)
    echo "blocked: could not scan the findings with grep (status $grc), so $file was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
    exit 2
    ;;
esac

# Cap the report at twenty paths, each cut at 200 bytes, so one bad file cannot flood the
# model's context with a finding per property. awk prints a last line, @@done, so an awk that
# did not run is told from one that found nothing.
arc=0
report="$(
  HOOK_FILE="$file" awk '
    NR <= 20 { printf "%s: %s\n", ENVIRON["HOOK_FILE"], substr($0, 1, 200) }
    END { if (NR > 20) printf "... and %d more\n", NR - 20; print "@@done" }
  ' <<<"$found"
)" || arc=$?
if [ "$arc" -ne 0 ] || [ "${report##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not format the findings (awk status $arc), so $file was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
report="${report%@@done}"
report="${report%$'\n'}"

{
  echo "blocked: $count object schema(s) in $file are not closed. Add \"additionalProperties\": false to each, and list every property in \"required\", so a strict provider mode accepts the schema and the model cannot add fields:"
  printf '%s\n' "$report"
} >&2
exit 2
