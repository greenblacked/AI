# Testing an MCP server

Read this before writing the tests for a server, or when reviewing a server whose tests
only call its handlers directly. A handler test shows that the function works; it does not
show what the model is shown, what a client receives on the wire, or whether the server
refuses the wrong caller. The checks below cover those three.

## Contents

- The tool-list snapshot
- MCP Inspector
- Error paths
- Output discipline on stdio
- Refusals on HTTP
- Does the model pick the right tool
- Running it in CI

## The tool-list snapshot

Store what `tools/list` returns in the repository and fail the test when it changes. The
snapshot holds each tool's name, description, input schema, output schema and annotations,
verbatim. Its job is to make every description edit a visible diff, because a description
change alters which tool a model chooses, and nothing else in the build notices it.

Capture it through the real server over its real transport, so the test sees what a client
sees rather than what your registration code intended:

```bash
set -Eeuo pipefail
npm ci --ignore-scripts --no-audit --no-fund --prefix tools/inspector
INSPECTOR=tools/inspector/node_modules/.bin/mcp-inspector
fresh="$(mktemp)"
status=0
out="$("$INSPECTOR" --cli node build/index.js --method tools/list --format json)" || status=$?
[ "$status" -eq 0 ] || { echo "inspector exited $status" >&2; exit "$status"; }
jq -S '.result.tools | sort_by(.name)' <<<"$out" > "$fresh"
diff -u tools.snapshot.json "$fresh"
```

The Inspector runs from `tools/inspector/`, a directory holding only a `package.json` and the
`package-lock.json` npm writes for it, both committed. Create them once with
`npm install --prefix tools/inspector --save-exact --ignore-scripts @modelcontextprotocol/inspector@<version>`.
Pinning the top-level version alone is not enough: `npx` resolves the Inspector's own
dependency ranges afresh on every clean runner, so a later transitive release changes the
code the gate runs. The lockfile records every package in the tree with an integrity hash,
and `npm ci` installs exactly that tree or fails, so review a change to the lockfile like a
change to the code. `--ignore-scripts` skips lifecycle scripts; the Inspector's own
`postinstall` only installs its clients in a source checkout and does nothing when it is a
dependency, so the CLI works without it (checked on 2.11.0).

`diff` exits non-zero on any difference, which fails the job. To accept a change, copy the
new file over the snapshot in the same commit as the code and have a person read the diff.
The Inspector flags above are those of its current documentation
([CLI smoke-testing guide](https://github.com/modelcontextprotocol/inspector/blob/main/docs/cli-smoke-testing.md));
they changed between its major versions, so run `--help` on the version you pin.

Details that decide whether the snapshot protects anything:

- Sorting by name, and sorting keys with `jq -S`, makes the snapshot order-insensitive. To
  test the server's own ordering, which 2026-07-28 says should be deterministic, drop the
  `sort_by(.name)` step.
- Snapshot only `.result.tools`. 2026-07-28 list results carry freshness fields such as
  `ttlMs` that are not part of the contract and may vary.
- If the list is paginated with `nextCursor`, follow the cursors until it is exhausted. A
  snapshot of the first page is a snapshot of part of the list.
- If the list varies with the caller's scopes, which 2026-07-28 allows, keep one snapshot per
  scope set, so the test shows what each kind of caller is offered.
- Require a reviewer for the snapshot file. A code-owners rule on it, or a review label,
  turns "someone edited a description" into "someone approved it".
- Treat a description diff as a behaviour change in review: read what the new wording
  tells the model to do, and whether it now overlaps a sibling.

You can do the same inside the SDK's own test client if you prefer one process. The contents
and the rules above do not change.

## MCP Inspector

The Inspector is the maintainers' tool for exercising a server. It needs Node 22.19.0 or
later according to its README. Three ways to use it:

```bash
npm ci --ignore-scripts --no-audit --no-fund --prefix tools/inspector
tools/inspector/node_modules/.bin/mcp-inspector                # web UI, for exploring
tools/inspector/node_modules/.bin/mcp-inspector --cli node build/index.js --method tools/list --format json
```

The Python SDK's `mcp dev server.py` command opens a server in the Inspector, per its
README.

How to use it well:

- Use the web UI while writing: list the tools, call each with good and bad input, and read
  the raw results. Look at what the model would see, not whether your handler returned.
- Use `--cli` for anything repeatable. Pass `--format json`, since the default output is for
  humans, and keep standard output and standard error apart: the result is on stdout and
  diagnostics on stderr, so merging them corrupts what `jq` reads.
- Install the Inspector in CI from the committed lockfile in `tools/inspector/`, as above,
  never through `npx`. The documentation notes that an unpinned `npx` run resolves the newest
  release each time and that a range such as `@2` is not a pin, and even an exact pin leaves
  the transitive tree to resolve afresh.
- Bound the connection with `--connect-timeout`, so a server that never starts fails the
  job rather than hanging it.
- Against an authenticated HTTP server in CI, pass `--stored-auth-only`, which fails with an
  authentication exit code instead of opening a browser and waiting. The flag does nothing
  against a server that never challenges, so a green run does not show your auth works;
  test the refusals separately, as below.
- Do not point the Inspector at production with a real token on a shared machine. Its README
  says it stores OAuth tokens and client secrets in the operating system keychain where
  available and otherwise in a file under the home directory, unencrypted unless you supply
  a key.

The CLI documents exit codes: 3 for an authentication challenge it could not satisfy, 4 for
an unreachable server and 5 for a tool error, meaning `isError: true` or a tool not found.
Capture the CLI's own status before `jq` runs, because with `pipefail` the rightmost failure
wins and the class is lost.

## Error paths

Call every tool with at least one input that should fail, and check that the result is a tool
execution error with a message the model can act on, not a crash and not a protocol error.

```bash
set -Eeuo pipefail
npm ci --ignore-scripts --no-audit --no-fund --prefix tools/inspector
INSPECTOR=tools/inspector/node_modules/.bin/mcp-inspector
status=0
out="$("$INSPECTOR" --cli node build/index.js \
  --method tools/call --tool-name get_ticket \
  --tool-args-json '{"ticket_id":"does-not-exist"}' --format json)" || status=$?
[ "$status" -eq 5 ]
jq -e '.result.isError == true and (.result.content[0].text | test("search_tickets"))' \
  <<<"$out" > /dev/null
```

The second assertion matters as much as the first: it checks that the message names the
tool that supplies a valid id. Assert on the content of the advice, not only the flag.

Cases to cover, per tool: a missing required argument, a wrong type, a value outside its
range, an extra unknown argument, a record that does not exist, and an upstream failure
(fake it). In 2025-11-25 and later, the spec classes input validation errors as tool
execution errors; 2025-06-18 listed invalid arguments as protocol errors, and an SDK may still
follow the older behaviour, so assert on what your SDK does and decide whether you accept it.
Use the SDK's test client for the cases the Inspector CLI cannot express.

Also test that errors leak nothing: assert the message holds no stack trace, file path,
connection string or token.

Pick a read-only, idempotent tool for any check that runs on every commit.

## Output discipline on stdio

A stdio server that writes anything but protocol to stdout fails in clients with a parse
error, and the cause is invisible in the server's own tests.

- Run the server as a subprocess from the test, send one request, read stdout to the response
  and assert that every line parses as a JSON-RPC message. Fail on any other byte.
- Capture stderr separately and assert it receives the server's log output, so you know
  logging is wired to the right stream.
- Add a static check as a cheap second layer. It is a heuristic, not a proof, since a library
  can still print:

```bash
set -Eeuo pipefail
if rg -n --glob '!**/node_modules/**' 'console\.log\(|^\s*print\(' src; then
  echo "stdout write in server source; log to stderr instead" >&2
  exit 1
fi
```

- Start the server with stdin closed and assert it exits promptly; 2026-07-28 says a stdio
  server should exit when standard input reaches end-of-file.

## Refusals on HTTP

For a remote server, test that the wrong caller is turned away. These checks need no
valid MCP exchange, since the refusal must happen before the body is acted on.

```bash
set -Eeuo pipefail
: "${MCP_URL:?set the MCP endpoint URL}"
: "${PROTOCOL_VERSION:?set a protocol version the server supports}"
: "${TOKEN_OTHER_AUDIENCE:?a valid token minted for a different resource}"
body='{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

status_of() {
  curl -s --max-time 10 -o /dev/null -w '%{http_code}' -X POST "$MCP_URL" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -H "MCP-Protocol-Version: $PROTOCOL_VERSION" \
    "$@" --data "$body"
}

[ "$(status_of -H 'Origin: https://attacker.example')" = 403 ]
[ "$(status_of)" = 401 ]
[ "$(status_of -H "Authorization: Bearer $TOKEN_OTHER_AUDIENCE")" = 401 ]
```

Add to this list, by running the same function with the right credentials: an expired token
(401), and a token that is valid but lacks the scope a write tool needs (403, with a
`WWW-Authenticate` header carrying `insufficient_scope`). Read the header with `curl -si`
or `-D -` for that last check.

Test fixtures need tokens for an authorisation server you control. Never put a production
token in a test, a log or a snapshot.

## Does the model pick the right tool

The snapshot proves the text has not changed. It does not prove the text works. Keep a short
list of real user requests, each paired with the tool it should select, and a few requests that
should select none of them. Run it against the model you target whenever descriptions change,
and count wrong selections. The `agent-evaluation` skill covers building that set and
reading the result; the point here is only that the set exists and is run on the same change
as the snapshot diff.

When two tools are confused in this check, the usual fix is a sentence in each description
saying when to use the other one, or merging them, not a longer description.

## Running it in CI

- Run the snapshot diff, the error-path checks and, for stdio, the output check on every
  pull request. They are fast and need no model or credential.
- Run the refusal checks against a staging deployment, with fixtures for tokens.
- Run the tool-selection check when a description changes, not on every commit, since it
  needs a model.
- Pin the Inspector and the SDK, and update both deliberately: a new SDK version can change
  the schema it generates from your types, which the snapshot will show as a diff you did not
  write.
