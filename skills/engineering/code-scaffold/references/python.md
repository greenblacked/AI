# Python idioms for production tools

A script that runs on a laptop and a tool that can be operated differ mostly in
structure: whether it imports without side effects, whether it reports failure in a way
a caller can branch on, and whether it says anything useful when it breaks at 3am.

## Contents

- [Structure: a `main(argv)` that returns an int](#structure-a-mainargv-that-returns-an-int)
- [Argument parsing and exit codes](#argument-parsing-and-exit-codes)
- [Logging](#logging)
- [Exceptions](#exceptions)
- [Input validation](#input-validation)
- [Configuration and secrets](#configuration-and-secrets)
- [Network calls](#network-calls)
- [Idempotence, atomic writes and cleanup](#idempotence-atomic-writes-and-cleanup)
- [Packaging](#packaging)
- [Validation](#validation)
- [Worked example](#worked-example)

## Structure: a `main(argv)` that returns an int

```python
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Work inside `main` returning an int means the module can be imported by a test, called
twice in one process, and reused as a library without executing anything on import.
`raise SystemExit(main())` turns that value into the process exit code at exactly one
place; `sys.exit()` scattered through helpers makes the same code unusable from anything
but a shell.

## Argument parsing and exit codes

```python
def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="sync-artifacts", description=__doc__)
    p.add_argument("--log-level", default="info", choices=("debug", "info", "warning", "error"))
    p.add_argument("--dry-run", action="store_true", help="print actions, change nothing")
    sub = p.add_subparsers(dest="command", required=True)
    push = sub.add_parser("push", help="upload artifacts")
    push.add_argument("--bucket", required=True)
    push.add_argument("--source", type=Path, required=True)
    sub.add_parser("verify", help="check the remote against the local manifest")
    return p.parse_args(argv)
```

Subcommands earn their place once two operations share configuration and flags. Below
that they are ceremony and one parser is clearer.

`argparse` already exits `2` on an unrecognised flag or a missing required argument,
which is where the convention's `2` comes from. Return `2` from your own validation
failures too, so a CI step can treat "the invocation is wrong" as one class regardless
of whether argparse or your code caught it.

```python
try:
    config = load_config(args)
except ConfigError as err:  # bad input, whoever supplied it
    log.error("configuration invalid: %s", err)
    return 2
except UpstreamError as err:  # the world is broken, not the invocation
    log.error("upstream failed: %s", err)
    return 1
```

## Logging

Configure logging once, in `main`, never at import time — a module that calls
`basicConfig` on import fights whatever the application already set up.

```python
log = logging.getLogger("sync-artifacts")


def configure_logging(level: str, json_output: bool = False) -> None:
    handler = logging.StreamHandler(sys.stderr)  # the default; be explicit anyway
    handler.setFormatter(
        JsonFormatter()
        if json_output
        else logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
        )
    )
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)
```

JSON mode is worth its ten lines wherever logs are aggregated: a searchable field beats
a regex over free text. Use lazy interpolation — `log.info("uploaded %s", key)`, not an
f-string — so formatting is skipped at filtered levels and aggregators can group by
message template.

Two habits cost more than anything else here. `print` for diagnostics puts progress
messages on stdout, corrupting piped output and losing both level filtering and separate
redirection. A bare `except:` catches `KeyboardInterrupt` and `SystemExit` as well as
errors, turning Ctrl-C into a silent continue and a loud failure into a wrong answer
that surfaces days later.

## Exceptions

A small hierarchy lets callers — including your own `main` — tell classes of failure
apart without matching on message text:

```python
class ToolError(Exception):
    """Base for errors this tool raises deliberately."""


class ConfigError(ToolError):
    """Invalid configuration or arguments."""


class UpstreamError(ToolError):
    """A dependency failed: API, database, filesystem."""
```

Catch narrowly and preserve the chain:

```python
try:
    resp = session.get(url, timeout=(5, 30))
    resp.raise_for_status()
except requests.RequestException as err:
    raise UpstreamError(f"fetching {url} failed") from err
```

`from err` keeps the original traceback attached; without it the traceback shows your
wrapper and hides the socket error that actually explains the outage. `except Exception`
is the widest catch ever appropriate — it leaves `KeyboardInterrupt` and `SystemExit`,
both `BaseException` rather than `Exception`, free to propagate.

## Input validation

Coerce types explicitly rather than trusting that a value is what it looks like.

```python
@dataclass(frozen=True)
class Settings:
    bucket: str
    source: Path
    max_workers: int

    def __post_init__(self) -> None:
        if not self.bucket:
            raise ConfigError("bucket must not be empty")
        if not self.source.is_dir():
            raise ConfigError(f"source is not a directory: {self.source}")
        if not 1 <= self.max_workers <= 32:
            raise ConfigError(f"max_workers out of range: {self.max_workers}")
```

`pathlib` beats string paths: `Path.resolve()`, `.is_dir()` and `/` composition remove a
whole category of join-and-quote bugs. For a path supplied from outside, resolve it then
check containment — `resolved.relative_to(base)` raises if the input escaped via `../`.

A frozen dataclass with `__post_init__` covers most scripts. Reach for `pydantic` when
the input is externally supplied structured data — a webhook body, a nested YAML config,
an API response you do not control — where its per-field errors and coercion repay the
dependency. For a tool with five flags it buys an import cost and a version constraint
and nothing else.

## Configuration and secrets

Resolve configuration in one direction, lowest precedence first: defaults, file,
environment, flags. Any other arrangement and two people will disagree about which value
wins, in production.

```python
values = {"bucket": None, "max_workers": 4}  # defaults
if args.config and args.config.exists():
    values.update(tomllib.loads(args.config.read_text()))  # file
for key in values:  # environment
    if (env := os.environ.get(f"SYNC_{key.upper()}")) is not None:
        values[key] = env
for key, val in vars(args).items():  # flags
    if key in values and val is not None:
        values[key] = val
```

Secrets come from the environment or a file, never a flag — a flag is visible in `ps`
and in CI job logs. Fail loudly when one is absent, because
`os.environ.get("API_TOKEN")` returning `None` produces an authentication failure three
layers down with no indication of the cause:

```python
try:
    token = os.environ["API_TOKEN"]
except KeyError:
    raise ConfigError("API_TOKEN is not set") from None
```

Never log the value, and watch the `repr` of any config object that holds one.

## Network calls

Every call gets an explicit timeout. `requests` and `urllib` default to no timeout at
all, so a socket that never responds hangs the process forever — the most common cause
of a scheduled job that quietly stops running and never alerts.

```python
def build_session(total_retries: int = 3) -> requests.Session:
    retry = Retry(
        total=total_retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD", "PUT", "DELETE"}),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


resp = session.get(url, timeout=(5, 30))  # (connect, read) — required, not optional
```

Restrict retries to idempotent methods; retrying a `POST` that succeeded but whose
response was lost is how one request becomes two charges. `httpx` is the equivalent for
async or HTTP/2 — `httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0))` — and it does
have a default timeout, though set it explicitly regardless.

## Idempotence, atomic writes and cleanup

```python
def write_atomic(path: Path, data: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)  # atomic within one filesystem
    except BaseException:
        os.unlink(tmp)
        raise
```

`os.replace` either fully succeeds or leaves the previous file intact, so a crash
mid-write never leaves a truncated config for the next run to choke on. The temporary
file goes in the destination directory to keep the rename on one filesystem; `/tmp` is
usually a different one, where the operation degrades to a copy and loses atomicity.

Cleanup belongs in a context manager or `try/finally`, not at the end of the happy path,
and `SIGTERM` needs handling in a container so the orchestrator's grace period finishes
the current item instead of being spent waiting for `SIGKILL`:

```python
@contextmanager
def workspace() -> Iterator[Path]:
    d = Path(tempfile.mkdtemp(prefix="sync-"))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _on_term(signum: int, frame) -> None:
    global shutting_down
    shutting_down = True
    log.warning("received %s; finishing current item", signal.Signals(signum).name)


signal.signal(signal.SIGTERM, _on_term)
```

Call `os.umask(0o077)` early in `main` for anything that writes sensitive files, so they
are created private; a `chmod` afterwards leaves a window in which the file was readable
by everyone on the host.

## Packaging

Declare dependencies in `pyproject.toml` and use a `src/` layout, which stops tests from
importing the working directory instead of the installed package and so hiding a missing
dependency until deployment.

```toml
[project]
name = "sync-artifacts"
requires-python = ">=3.11"
dependencies = ["requests>=2.31,<3"]

[project.scripts]
sync-artifacts = "sync_artifacts.cli:main"
```

Libraries take ranges so consumers can resolve a shared version; applications pin
exactly in a lock file (`uv.lock`, `poetry.lock`, or `pip-compile` output committed as
`requirements.txt`). Without a lock, a transitive dependency shipping a breaking release
becomes a failed deploy that has nothing to do with your change.

## Validation

```bash
python -m py_compile tool.py     # syntax only, fast
ruff check .                     # lint
ruff format --check .            # formatting, no diff expected
mypy --strict src/               # drop --strict on a partially annotated codebase
pytest -q
```

Even a hundred-line script deserves three tests: `main([...])` returns `0` on the happy
path, `2` on a bad argument, `1` on an upstream failure. They are cheap precisely
because `main(argv)` is importable, which is the payoff for structuring it that way.

## Worked example

```python
#!/usr/bin/env python3
"""Publish a build artifact to a bucket. Safe to re-run; skips an existing key."""

from __future__ import annotations

import argparse, hashlib, logging, os, sys
from pathlib import Path

log = logging.getLogger("publish")


class ToolError(Exception): ...


class ConfigError(ToolError): ...


class UpstreamError(ToolError): ...


def main(argv: list[str] | None = None) -> int:
    # parse_args() builds --bucket, --artifact, --dry-run and --log-level as shown above
    args = parse_args(argv if argv is not None else sys.argv[1:])
    logging.basicConfig(
        level=args.log_level.upper(),
        force=True,
        handlers=[logging.StreamHandler(sys.stderr)],
        format="%(asctime)s %(levelname)s %(message)s",
    )
    os.umask(0o077)
    try:
        if not args.artifact.is_file():
            raise ConfigError(f"artifact not found: {args.artifact}")
        if not (token := os.environ.get("API_TOKEN")):
            raise ConfigError("API_TOKEN is not set")

        digest = hashlib.sha256(args.artifact.read_bytes()).hexdigest()
        key = f"artifacts/{digest}/{args.artifact.name}"
        if remote_exists(args.bucket, key, token):
            log.info("already published: s3://%s/%s", args.bucket, key)
            return 0
        if args.dry_run:
            log.info("DRY-RUN: would upload %s to s3://%s/%s", args.artifact, args.bucket, key)
            return 0
        upload(args.bucket, key, args.artifact, token)
        log.info("published s3://%s/%s", args.bucket, key)
        return 0
    except ConfigError as err:
        log.error("%s", err)
        return 2
    except UpstreamError as err:
        log.error("%s", err)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```
