#!/usr/bin/env bash
# A `git bisect run` probe that survives a slightly flaky test.
#
# The exit code is the whole contract with git bisect:
#   0            this commit is good
#   1-127 (≠125) this commit is bad
#   125          this commit cannot be tested — skip it rather than blaming it
#   128+         abort the bisect
#
# Requiring three consecutive failures before calling a commit bad costs two extra
# runs and buys the difference between an answer and a confident wrong answer. If the
# failure is much below 100% reproducible, quarantine the test and stabilise it first;
# no number of retries rescues a bisect over noise.
#
# Adapt BUILD_CMD, TEST_CMD and RUNNER to the project, together: RUNNER is the binary
# TEST_CMD needs. Everything else is the contract.
set -uo pipefail

readonly ATTEMPTS="${BISECT_ATTEMPTS:-3}"
readonly BUILD_CMD="${BISECT_BUILD_CMD:-npm ci --prefer-offline}"
# The runner comes from this commit's own lockfile. `npx jest` would fetch today's release
# from the registry when the commit has none, and judge old code with a runner it never had.
readonly TEST_CMD="${BISECT_TEST_CMD:-node_modules/.bin/jest path/to/suspect.test.ts}"
# The binary TEST_CMD needs, checked before the first attempt. Change it whenever
# TEST_CMD changes; set it empty for a command with no runner this commit could lack.
readonly RUNNER="${BISECT_RUNNER-node_modules/.bin/jest}"

log() { printf '%s bisect-probe: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }

# A commit that cannot be built is untestable, not bad. Marking it bad moves the
# bisect boundary to the wrong place and every later step inherits the error.
if ! eval "$BUILD_CMD"; then
  log "build failed - skipping this commit"
  exit 125
fi

# A runner this commit's lockfile did not install makes the commit untestable, not bad.
# This is checked up front rather than read back from the exit status: a launched test
# command may itself return 126 or 127, and that is a real failure.
if [ -n "$RUNNER" ] && [ ! -x "$RUNNER" ]; then
  log "no executable $RUNNER at this commit - skipping"
  exit 125
fi

for attempt in $(seq 1 "$ATTEMPTS"); do
  status=0
  eval "$TEST_CMD" || status=$?
  if [ "$status" -eq 0 ]; then
    log "attempt $attempt/$ATTEMPTS passed - commit is good"
    exit 0
  fi
  log "attempt $attempt/$ATTEMPTS failed"
done

log "failed $ATTEMPTS/$ATTEMPTS - commit is bad"
exit 1
