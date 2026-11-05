#!/usr/bin/env bash
# Refuse a mutation-testing suppression written without a reason. Deterministic: standard
# tools only, no network, no secrets.
set -Eeuo pipefail

input="$(cat)"
file_path=""
text=""
# Either parser prints nothing, and the hook allows, for input it cannot read text from:
# invalid JSON, a non-object, a missing tool_input, or neither content nor new_string.
if command -v jq >/dev/null 2>&1; then
  file_path="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.file_path | if type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
  text="$(printf '%s' "$input" | jq -r \
    'if type=="object" and (.tool_input|type)=="object" then (.tool_input.content // .tool_input.new_string | if . == null then empty elif type=="string" then . else empty end) else empty end' \
    2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
  parse='import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = None
tool = data.get("tool_input") if isinstance(data, dict) else None
value = None
if isinstance(tool, dict):
    if sys.argv[1] == "file_path":
        value = tool.get("file_path")
    else:
        value = tool.get("content")
        if value is None:
            value = tool.get("new_string")
print(value if isinstance(value, str) else "")'
  file_path="$(printf '%s' "$input" | python3 -I -c "$parse" file_path || true)"
  text="$(printf '%s' "$input" | python3 -I -c "$parse" text || true)"
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

# Neither parser present, or nothing to judge: allow, because a hook that blocks everything
# on a missing tool is worse than no hook.
[ -n "$text" ] || exit 0

# Only source code carries these markers; a README or a test report that quotes one is not a
# suppression. No path means nothing to judge.
case "$file_path" in
  *.py | *.js | *.jsx | *.mjs | *.cjs | *.ts | *.tsx | *.rs | *.php | *.java | *.kt | *.scala | *.cs | *.rb | *.go | *.swift | *.mts | *.cts | *.vue | *.svelte) ;;
  *) exit 0 ;;
esac

# Text that holds a marker and is larger than 1 MiB is refused rather than judged: no real edit
# is near that size, and a whole-file Write of generated code can be a few hundred KiB. The awk
# pass below is linear, so the limit is a bound on the work and not a guard against a quadratic
# case; a hook that outlasts its timeout fails open.
if hits "$text" -E 'Stryker disable|pragma: no mutate|mutants::skip|infection-ignore'; then
  if [ "$(printf '%s' "$text" | wc -c)" -gt 1048576 ]; then
    echo "blocked: the text holds a mutation suppression marker and is larger than 1 MiB, which this hook will not judge. Write the suppression in a smaller edit, with its reason in the same edit." >&2
    exit 2
  fi
else
  exit 0
fi

# Judged on the written text alone, so for an Edit the reason must be in the same edit.
# A reason is words in a comment on the same line or the line directly above, or text after
# the colon on a Stryker line. One awk pass reads every line, so a marker line costs no
# process and no expansion of a long line.
# The awk runs byte-wise (LC_ALL=C), so it cannot ask whether a character is a letter. norm()
# approximates grep's UTF-8 [[:alpha:]]: a multibyte character counts as one letter when its lead
# byte starts a block that is mostly letters (Latin, Greek, Cyrillic, Hebrew, Arabic, Indic, CJK
# and the like), and as a non-letter otherwise: \302 (U+0080-00BF, NBSP and the Latin-1
# punctuation), \342 (U+2000-2FFF, ellipsis, dashes, arrows, symbols), \356 (private use) and
# \360-\364 (emoji and the other supplementary planes). It is an approximation: a few letters in
# an excluded block (ª, º, µ, the letterlike symbols, the rarer CJK ideographs) count as
# non-letters, and some marks and symbols in an included block (combining marks, the modifier
# letters, private use) count as letters. The multiplication and division signs, the CJK punctuation
# block and the fullwidth and special-purpose punctuation are removed first. The CJK block holds
# letters too, which stay: the iteration mark and the other ideographic letters (U+3005-3007,
# so 人々 and 時々 are words), and the vertical kana repeat marks and the vertical ideographic
# iteration mark (U+3031-3035, U+303B). The hiragana and katakana repeat marks (ゝ ゞ ヽ ヾ) are
# outside the CJK punctuation block and were never removed.
#   Stryker line: the reason is what follows the first colon after "Stryker disable".
#   Other marker: the reason must come after the marker (code before it is not one, and a
#   suffix such as the "-all" in @infection-ignore-all belongs to the marker), or sit in a
#   comment line directly above that is not itself a marker. A Rust attribute (#[inline]) or
#   a shebang (#!) is not a comment, and a bare `*` leader counts only as a docblock line
#   (` * reason`): `*count += 1;` is code.
# awk prints a last line, @@done, so that an awk that did not run (the here-string failed to
# write, awk was killed) is told from one that found nothing wrong.
rc=0
verdict="$(
  LC_ALL=C awk '
    function norm(s) {
      gsub(/\303\227|\303\267|\343\200[\200-\204\210-\260\266-\272\274-\277]|\357\274[\200-\217\232-\240\273-\277]|\357\275[\200\233-\245]|\357\273\277|\357\277[\260-\277]/, " ", s)
      gsub(/[\303-\341\343-\355\357][\200-\277]*/, "a", s)
      gsub(/[\200-\377]/, " ", s)
      return s
    }
    function words(s) { return norm(s) ~ /[A-Za-z][A-Za-z]/ }
    function marked(s) {
      return index(s, "pragma: no mutate") || index(s, "mutants::skip") || index(s, "infection-ignore")
    }
    {
      line = $0
      if (index(line, "Stryker disable")) {
        rest = substr(line, index(line, "Stryker disable") + length("Stryker disable"))
        colon = index(rest, ":")
        reason = colon ? norm(substr(rest, colon + 1)) : ""
        if (reason !~ /[A-Za-z0-9]/) printf "line %d: %s\n", NR, line
      } else if (marked(line)) {
        m = "pragma: no mutate"
        at = index(line, m)
        if (!at) { m = "mutants::skip"; at = index(line, m) }
        if (!at) { m = "infection-ignore"; at = index(line, m) }
        after = norm(substr(line, at + length(m)))
        sub(/^(-[A-Za-z]+)*/, "", after)
        same = after ~ /[A-Za-z][A-Za-z]/
        above = 0
        lead = prev
        sub(/^[[:space:]]+/, "", lead)
        two = substr(lead, 1, 2)
        if (marked(lead) || two == "#[" || two == "#!") {
        } else if (substr(lead, 1, 1) == "#" || two == "//" || two == "/*" || two == "* " || two == "*\t" || lead == "*") {
          above = words(prev)
        }
        if (!same && !above) printf "line %d: %s\n", NR, line
      }
      prev = line
    }
    END { print "@@done" }
  ' <<<"$text"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan the text for mutation suppressions (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
missing="${verdict%@@done}"
missing="${missing%$'\n'}"

if [ -n "$missing" ]; then
  {
    echo "blocked: a mutation suppression needs a reason. Say why the mutant is equivalent or accepted,"
    echo "on the same line or in a comment directly above, within this same write or edit:"
    printf '%s\n' "$missing"
  } >&2
  exit 2
fi
exit 0
