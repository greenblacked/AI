#!/usr/bin/env bash
# Report a written GitHub Actions workflow whose run or script block expands a field an outsider
# controls. The expression is substituted into the command text before the shell parses it, so a
# pull request title with shell syntax in it runs with the job's token; passing the value through
# an env: variable makes it a shell argument instead. Deterministic: standard tools only, no
# network, no secrets, nothing run from the file.
#
# What it checks. For a written file directly under .github/workflows/ whose name ends in .yml or
# .yaml, the file is read from disk at tool_input.file_path, so an Edit is judged on the whole file
# and not on its fragment. One pass tracks each run: or script: key (also as a list item) and the
# lines indented under it, and reports a line there that has an expression opener followed by one
# of: github.head_ref, or a github.event field for a pull request title, body, head ref, label,
# head repository default branch or head repository description; an issue title or body; a comment,
# review or review comment body; a discussion title or body; the message, author name or author
# email of the head commit or of any commit in a push (commits[N] or commits[*]); the name of a
# page in a wiki event; a workflow run head branch, display title or head commit message. The
# expression is compared in lower case, because GitHub reads property names without regard to
# case, so github.event.Pull_Request.TITLE is the same field. Comment lines outside a block are skipped. A line inside a block is
# judged even when it is a shell comment, because the substitution happens before any shell sees it.
# A finding exits 2 and names path:line for up to 20 lines; any other file, or none, is allowed.
#
# Known limits.
#   - PostToolUse: the write has already happened. Exit 2 only feeds stderr back to the model, which
#     can fix the file; the hook cannot undo anything.
#   - Indirection is invisible: a value carried through inputs, a step output, a matrix entry or an
#     env: variable that is later expanded again. So are toJSON, bracket spellings of github.event,
#     and fields this list does not name. GitLab CI is not read.
#   - An expression is read on its own line. One that spans lines is not seen, and one that reduces
#     to a boolean, such as a comparison of the title, is flagged although it carries no text.
#   - A key called run or script outside a step is read as a step; it is flagged only if it
#     also holds such an expression. A flow-style step on one line is not read.
#   - Only the file on disk after the write is judged, never a shell command that creates one.
#     A file over 1 MiB is refused, not scanned.
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

# .github/workflows/*.yml and *.yaml, at the top level only: GitHub does not read a workflow in a
# subdirectory. The leading slash lets one pattern cover a relative and an absolute path.
path="/$file"
case "$path" in
  */.github/workflows/*.yml | */.github/workflows/*.yaml) ;;
  *) exit 0 ;;
esac
case "${path##*/.github/workflows/}" in
  */*) exit 0 ;;
esac
[ -f "$file" ] || exit 0

# From here the file is judged, and a hook that cannot read it must say so rather than let it
# through. A missing tool is exit 127 in a command substitution, which `set -e` would turn
# into a silent failure, so check for each tool by name first.
for tool in grep awk wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "blocked: $tool is not installed, so this hook cannot read $file and did not judge it. Install $tool (any POSIX version), or check the workflow for untrusted fields in run blocks yourself." >&2
    exit 2
  fi
done

# The file is only ever a redirection source, never an argument, so a name starting with a
# dash cannot be read as an option.
rc=0
size="$(wc -c <"$file")" || rc=$?
size="${size##* }"
if [ "$rc" -ne 0 ] || [ -z "$size" ]; then
  echo "blocked: could not read $file to check it for untrusted fields in run blocks. Check the file is readable, then retry." >&2
  exit 2
fi
# No real workflow is near this size. The scan below is linear, so the limit bounds the work; a
# hook that outlasts its timeout fails open.
if [ "$size" -gt 1048576 ]; then
  echo "blocked: $file is larger than 1 MiB, which this hook will not scan. A workflow is far smaller; check what was written to it." >&2
  exit 2
fi

# grep exits 0 for a match, 1 for none and 2 or more when it could not read the file; only the
# first two are an answer. A file with no double brace has no expression to judge.
rc=0
grep -q '{{' <"$file" || rc=$?
case "$rc" in
  0) ;;
  1) exit 0 ;;
  *)
    echo "blocked: could not read $file to check it for untrusted fields in run blocks. Check the file is readable, then retry." >&2
    exit 2
    ;;
esac

# One awk pass. The expression opener is built from fragments, here and nowhere else, so this
# script carries no literal expression that a scanner could read as a sink. A line is split on the
# opener once, which is linear in its length; each piece is cut at the first closer and compared
# with the field names by plain substring search, so there is no regex to backtrack. awk prints a
# last line, @@done, so that an awk that did not run (killed, or the redirection failed) is told
# from one that found nothing wrong.
rc=0
verdict="$(
  awk '
    function wild(expr, w,   a, b, rest, p, q) {
      a = W1[w]
      b = W2[w]
      rest = expr
      while ((p = index(rest, a)) > 0) {
        rest = substr(rest, p + length(a))
        q = index(rest, "]")
        if (q && substr(rest, q + 1, length(b)) == b) return 1
      }
      return 0
    }
    function check(s,   n, k, j, part, e, expr) {
      if (index(s, "{{") == 0) return 0
      s = tolower(s)
      n = split(s, P, SEP)
      for (k = 2; k <= n; k++) {
        part = P[k]
        e = index(part, CLOSE)
        expr = e ? substr(part, 1, e - 1) : part
        if (index(expr, "github.") == 0) continue
        for (j = 1; j <= nf; j++) if (index(expr, F[j])) return 1
        for (j = 1; j <= nw; j++) if (wild(expr, j)) return 1
      }
      return 0
    }
    function report() {
      nfind++
      if (nfind <= 20) out = out NR ":" substr($0, 1, 120) "\n"
    }
    BEGIN {
      SEP = "\\$" "\\{" "\\{"
      CLOSE = "}" "}"
      list = "github.head_ref"
      list = list " github.event.pull_request.title github.event.pull_request.body"
      list = list " github.event.pull_request.head.ref github.event.pull_request.head.label"
      list = list " github.event.pull_request.head.repo.default_branch"
      list = list " github.event.pull_request.head.repo.description"
      list = list " github.event.issue.title github.event.issue.body"
      list = list " github.event.comment.body github.event.review.body"
      list = list " github.event.review_comment.body"
      list = list " github.event.discussion.title github.event.discussion.body"
      list = list " github.event.head_commit.message github.event.head_commit.author.name"
      list = list " github.event.head_commit.author.email"
      list = list " github.event.workflow_run.head_branch github.event.workflow_run.display_title"
      list = list " github.event.workflow_run.head_commit.message"
      nf = split(list, F, " ")
      # An entry that carries an index: the text before the bracket and the text after it.
      nw = 0
      wl = "commits[|.message commits[|.author.name commits[|.author.email pages[|.page_name"
      n = split(wl, T, " ")
      for (j = 1; j <= n; j++) {
        nw++
        split(T[j], U, "|")
        W1[nw] = "github.event." U[1]
        W2[nw] = U[2]
      }
    }
    {
      sub(/\r$/, "")
      if ($0 ~ /^[ \t]*$/) next
      if (inb) {
        match($0, /^ */)
        if (RLENGTH > t) {
          if (check($0)) report()
          next
        }
        inb = 0
      }
      match($0, /^ *(- +)*/)
      i = RLENGTH + 1
      if (substr($0, i, 1) == "#") next
      key = substr($0, i, 7)
      if (substr(key, 1, 4) == "run:") klen = 4
      else if (key == "script:") klen = 7
      else next
      inb = 1
      t = i - 1
      if (check(substr($0, i + klen))) report()
    }
    END {
      if (nfind) {
        printf "%s", out
        if (nfind > 20) printf "%d:%d more lines not shown\n", NR, nfind - 20
      }
      print "@@done"
    }
  ' <"$file"
)" || rc=$?
if [ "$rc" -ne 0 ] || [ "${verdict##*$'\n'}" != "@@done" ]; then
  echo "blocked: could not scan $file for untrusted fields in run blocks (awk status $rc), so it was not judged. Retry; if it repeats, check free space in the temporary directory." >&2
  exit 2
fi
finding="${verdict%@@done}"
finding="${finding%$'\n'}"

if [ -n "$finding" ]; then
  {
    echo "blocked: $file expands a field an outsider controls inside a run or script block. The substitution happens before the shell parses the line, so the value runs as shell syntax with the job's token. The write already happened; fix it now."
    printf '%s\n' "$finding" | while IFS= read -r line; do
      printf '%s:%s\n' "$file" "$line"
    done
    echo "Move the value to an env: variable on the step and read it as \"\$NAME\" in the block. Quoting the expression does not help."
  } >&2
  exit 2
fi
exit 0
