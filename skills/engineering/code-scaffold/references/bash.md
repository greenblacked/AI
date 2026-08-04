# Bash idioms for production scripts

Bash defaults are tuned for an interactive shell, where a failed command is obvious
because a human is watching. In a cron job nobody is watching, so those defaults have
to be overridden deliberately.

## Strict mode, and what it does not catch

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
```

- `-e` exits on an unchecked non-zero status.
- `-E` makes the `ERR` trap inherit into functions, subshells and command
  substitutions; without it an error inside a function goes unreported.
- `-u` treats an unset variable as an error, turning `rm -rf "$PREFIX/"` with an empty
  `PREFIX` into an exit rather than a wiped root.
- `-o pipefail` returns the first non-zero status in a pipeline instead of the last
  command's.
- `IFS=$'\n\t'` drops the space from word splitting, so an unquoted expansion holding a
  filename with a space splits on lines and tabs only.

`set -e` is not a safety net. It does not fire when:

```bash
false && echo hi          # non-final command in a && / || chain
if false; then :; fi      # anywhere in an if/while/until condition
! false                   # negated
false | true              # non-final pipeline element, without pipefail
```

The subtle one is assignment through a builtin:

```bash
local version=$(curl -sf "$url")   # exit status is local's, which is 0. Bug.
```

`local`, `declare`, `export` and `readonly` return their own status and mask the
substitution's. Split the declaration from the assignment:

```bash
local version
version=$(curl -sf "$url")         # now set -e sees the failure
```

`set -u` also bites on empty arrays in Bash 4.3 and earlier — `"${arr[@]}"` errors when
`arr` is empty. Require 4.4+ and check it, or write `"${arr[@]+"${arr[@]}"}"`.

## Traps: cleanup and error reporting

Register cleanup before creating anything that needs it, so an early failure still tidies up.

```bash
TMPDIR_RUN=""

cleanup() {
  local rc=$?                       # capture before anything else changes it
  [[ -n "$TMPDIR_RUN" && -d "$TMPDIR_RUN" ]] && rm -rf "$TMPDIR_RUN"
  return "$rc"
}
err_trap() {
  local rc=$? line=$1 cmd=$2
  log error "failed at ${BASH_SOURCE[1]}:${line} (rc=${rc}): ${cmd}"
}
trap 'err_trap "${BASH_LINENO[0]}" "$BASH_COMMAND"' ERR
trap cleanup EXIT
trap 'log warn "interrupted"; exit 130' INT TERM
```

`BASH_COMMAND` holds the command that was about to run and `BASH_LINENO[0]` the line
that called into the trap — the difference between a five-minute diagnosis and an hour
of adding `echo` statements to a live script.

## Logging to stderr

```bash
LOG_LEVEL="${LOG_LEVEL:-info}"

log() {
  local level=$1; shift
  local -A rank=([debug]=10 [info]=20 [warn]=30 [error]=40)
  (( ${rank[$level]:-20} < ${rank[$LOG_LEVEL]:-20} )) && return 0
  printf '%s [%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${level^^}" "$*" >&2
}
```

Everything goes to `>&2`. The moment a diagnostic lands on stdout the script stops
being usable in a pipeline, and something downstream parses `[INFO] starting` as data.

## Argument parsing

`getopts` is built in and handles clustering and `-o value`. Use it when short flags
are enough:

```bash
while getopts ":b:p:nh" opt; do
  case $opt in
    b) BUCKET=$OPTARG ;;  p) PREFIX=$OPTARG ;;  n) DRY_RUN=1 ;;  h) usage ;;
    :) log error "-$OPTARG needs a value"; exit 2 ;;
    \?) log error "unknown option: -$OPTARG"; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
```

It has no long options, so anything a human types by hand gets a `while case` loop:

```bash
usage() {
  cat >&2 <<'EOF'
Usage: sync-artifacts.sh --bucket NAME --prefix PATH [--dry-run] [--log-level LEVEL]
  --dry-run           Print actions without executing them
  --log-level LEVEL   debug|info|warn|error (default: info)
EOF
  exit 2
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --bucket)    BUCKET=${2:-}; shift 2 ;;
    --prefix)    PREFIX=${2:-}; shift 2 ;;
    --dry-run)   DRY_RUN=1; shift ;;
    --log-level) LOG_LEVEL=${2:-}; shift 2 ;;
    -h|--help)   usage ;;
    --)          shift; break ;;
    -*)          log error "unknown option: $1"; usage ;;
    *)           break ;;
  esac
done

[[ -n "$BUCKET" ]] || { log error "--bucket is required"; usage; }
[[ "$PREFIX" =~ ^[A-Za-z0-9._/-]+$ ]] || { log error "--prefix: invalid characters"; exit 2; }
command -v aws >/dev/null || { log error "aws CLI not found on PATH"; exit 2; }
```

Validation sits here, before the first mutation; a script that validates halfway
through leaves the system in a state nobody planned for. `usage` exits 2 to match the
exit-code table — usage and validation errors are `2`, runtime failures are `1`.

## Quoting, tests and arrays

Quote every expansion unless you have a specific reason not to. Unquoted `$var`
undergoes word splitting and glob expansion, so a path with a space becomes two
arguments and a filename containing `*` expands against the current directory. Prefer
`[[ ]]` to `[ ]`: it does not word-split its operands, supports `=~` and `&&`, and will
not misparse an empty variable as a missing operand. Build commands as arrays, never as
a string:

```bash
args=(aws s3 sync "$src" "s3://${BUCKET}/${PREFIX}" --only-show-errors)
(( DRY_RUN )) && args+=(--dryrun)
"${args[@]}"
```

A command held in a string and expanded unquoted re-splits on whitespace and mangles
any argument containing a space; `eval` on that same string turns a filename into a
code-execution path.

## Idempotence, temporary files and dry-run

`TMPDIR_RUN=$(mktemp -d "${TMPDIR:-/tmp}/sync.XXXXXX")` gives a `0700` directory with an
unpredictable name, avoiding the symlink race a fixed `/tmp/myscript.tmp` invites; the
`EXIT` trap above removes it on every path, including failure and `Ctrl-C`. Then assume
a second run, and use the cheap idioms:

```bash
mkdir -p "$dest"                                  # no error if it exists
install -D -m 0640 config.tmpl "$dest/config"     # creates parents, sets mode in one step
id -u svcuser >/dev/null 2>&1 || useradd -r svcuser
[[ -f "$STAMP" ]] && { log info "already applied; nothing to do"; exit 0; }
```

Thread `--dry-run` through one wrapper rather than sprinkling `if` blocks:

```bash
run() { if (( DRY_RUN )); then log info "DRY-RUN: $*"; else "$@"; fi; }

run rm -rf "$stale_dir"
run install -D -m 0640 "$TMPDIR_RUN/config" "$dest/config"
```

Anything irreversible gets a flag or a confirmation, not a comment saying "be careful".

## Network calls and timeouts

```bash
curl --silent --show-error --location --fail-with-body \
     --connect-timeout 5 --max-time 30 \
     --retry 3 --retry-all-errors --retry-delay 2 \
     --output "$TMPDIR_RUN/payload.json" "$url"
```

`--fail-with-body` returns non-zero on HTTP >= 400 while still writing the response, so
the error message survives; plain `--fail` discards it, and `-s` alone exits 0 on a 500
and hands you an HTML error page as your JSON. `--retry-all-errors` is what makes
`--retry` cover connection resets rather than only 5xx. For anything without its own
timeout flag, wrap it — `timeout 60 pg_dump ...`, or `timeout --kill-after=10 60 ...`
when the command ignores `SIGTERM`. A call with no timeout is how a cron job stops
firing forever without ever alerting.

## Secrets

Read them from the environment or a file, never an argument:

```bash
if [[ -n "${API_TOKEN_FILE:-}" ]]; then
  API_TOKEN=$(<"$API_TOKEN_FILE")
elif [[ -z "${API_TOKEN:-}" ]]; then
  log error "set API_TOKEN or API_TOKEN_FILE"; exit 2
fi
curl --header @<(printf 'Authorization: Bearer %s\n' "$API_TOKEN") ...
```

An argument is visible in `ps aux` and `/proc/<pid>/cmdline` to every user on the box
for the life of the process, it lands in `~/.bash_history`, and CI runners echo command
lines into logs retained far longer than the credential is valid. Never
`log info "token=$API_TOKEN"`, and `umask 077` before writing any file that holds one.

## Locking

Anything cron-driven needs a lock: the previous run overrunning is the normal case.

```bash
exec 9>"/var/lock/sync-artifacts.lock"
flock -n 9 || { log warn "another run in progress; exiting"; exit 0; }
```

The lock releases when the descriptor closes, so it survives a `kill -9` where a PID
file would not. Exit `0` if an overlap is routine, or a distinct code if the caller
should treat it as notable.

## Validation

```bash
bash -n script.sh                       # parse only, catches syntax errors
shellcheck -x -S style script.sh        # -x follows sourced files
shfmt -i 2 -ci -d script.sh             # diff against canonical formatting
```

Silence a ShellCheck finding only with a reason on the line above:

```bash
# shellcheck disable=SC2016  # single quotes intended: awk expands $1, not the shell
awk '{print $1}' "$file"
```

Worth recognising before reaching for a disable: `SC2086` (unquoted expansion, almost
always a real bug), `SC2155` (declare and assign separately — the masked exit status
above), `SC2164` (`cd` without `|| exit`), `SC2015` (`a && b || c` is not if-then-else).

## Worked example

```bash
#!/usr/bin/env bash
# Publish a build artifact to a bucket. Safe to re-run; skips an already-published one.
set -Eeuo pipefail
IFS=$'\n\t'

readonly LOCK_FILE="/var/lock/publish-artifact.lock"
LOG_LEVEL="${LOG_LEVEL:-info}"
DRY_RUN=0; BUCKET=""; ARTIFACT=""; TMPDIR_RUN=""

log() { :; }   # the level-filtered, stderr-writing log() shown above
cleanup() { local rc=$?; [[ -d "${TMPDIR_RUN:-}" ]] && rm -rf "$TMPDIR_RUN"; return "$rc"; }
err_trap() { log error "failed at line $1 (rc=$?): $2"; }
trap 'err_trap "${BASH_LINENO[0]}" "$BASH_COMMAND"' ERR
trap cleanup EXIT

usage() { echo "Usage: publish-artifact.sh --bucket NAME --artifact PATH [--dry-run]" >&2; exit 2; }
run() { if (( DRY_RUN )); then log info "DRY-RUN: $*"; else "$@"; fi; }

main() {
  parse_args "$@"        # the while/case loop shown above, setting BUCKET/ARTIFACT/DRY_RUN

  [[ -n "$BUCKET" ]]   || { log error "--bucket is required"; usage; }
  [[ -f "$ARTIFACT" ]] || { log error "artifact not found: ${ARTIFACT:-unset}"; exit 2; }
  command -v aws >/dev/null || { log error "aws CLI not on PATH"; exit 2; }

  exec 9>"$LOCK_FILE"
  flock -n 9 || { log warn "another run in progress; exiting"; exit 0; }
  TMPDIR_RUN=$(mktemp -d "${TMPDIR:-/tmp}/publish.XXXXXX")

  local checksum key
  checksum=$(sha256sum "$ARTIFACT" | cut -d' ' -f1)
  key="artifacts/${checksum}/$(basename "$ARTIFACT")"

  if aws s3api head-object --bucket "$BUCKET" --key "$key" >/dev/null 2>&1; then
    log info "already published: s3://${BUCKET}/${key}"; exit 0
  fi

  log info "publishing ${ARTIFACT} to s3://${BUCKET}/${key}"
  run aws s3 cp "$ARTIFACT" "s3://${BUCKET}/${key}" --only-show-errors
  log info "done in ${SECONDS}s"
}

main "$@"
```
