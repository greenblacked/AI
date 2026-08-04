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
# Adapt BUILD_CMD and TEST_CMD to the project. Everything else is the contract.
set -uo pipefail

readonly ATTEMPTS="${BISECT_ATTEMPTS:-3}"
readonly BUILD_CMD="${BISECT_BUILD_CMD:-npm ci --prefer-offline}"
readonly TEST_CMD="${BISECT_TEST_CMD:-npx jest path/to/suspect.test.ts}"

log() { printf '%s bisect-probe: %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }

# A commit that cannot be built is untestable, not bad. Marking it bad moves the
# bisect boundary to the wrong place and every later step inherits the error.
if ! eval "$BUILD_CMD"; then
  log "build failed - skipping this commit"
  exit 125
fi

for attempt in $(seq 1 "$ATTEMPTS"); do
  if eval "$TEST_CMD"; then
    log "attempt $attempt/$ATTEMPTS passed - commit is good"
    exit 0
  fi
  log "attempt $attempt/$ATTEMPTS failed"
done

log "failed $ATTEMPTS/$ATTEMPTS - commit is bad"
exit 1
