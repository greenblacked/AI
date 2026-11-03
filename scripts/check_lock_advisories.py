#!/usr/bin/env python3
"""Look up the hashed requirement locks in OSV and fail on an advisory nobody accepted.

`.github/dependabot.yml` ignores everything in `.github/requirements/`, because a hash-pinned
lock has to be regenerated and a version line edited into one breaks the install (#362).
The cost is that nothing in the repository looks for new advisories against those locks;
Dependabot alerts still appear, but only on a Security tab nobody reads on a schedule.
This is that look. It runs weekly from `scheduled.yml`, where a red run is the intended
signal: a lock needs regenerating, or an advisory needs a reviewed acceptance.

A requirement line that is not a `name==version` pin (a VCS URL, `~=`, `===`) fails the run
rather than being skipped, since a skipped line is a package never audited. Every
`name==version` line in every `.github/requirements/*.txt` is audited, including a
line with an environment marker. The marker decides where a package installs, not whether
its version is vulnerable, and pip-audit drops win32-marker lines, which is why this
script exists rather than pip-audit.

One POST to `api.osv.dev/v1/querybatch` carries a query per (package, version), in batches
of at most the documented 1000. A result carrying `next_page_token` is re-sent with the
token until none is left, even when it lists no vulnerabilities: a timeout on OSV's side
can return a token and nothing else. Each advisory found is then fetched from
`/v1/vulns/{id}` for its summary, its aliases and its `withdrawn` field; a withdrawn
advisory is skipped. OSV rejects a whole batch if one query is invalid, so any non-2xx
response, timeout or unparseable body ends the run with exit 1. It fails closed: an audit
that could not run must not read as "no advisories".

`.github/requirements/advisories-accepted.json` is a list of `{id, package, reason,
expires}`. An entry needs a reason and an ISO `expires` no more than 180 days ahead; an
expired or invalid entry fails the run, and one that matches nothing is a warning. An
accepted GHSA covers the PYSEC or CVE id of the same advisory, because OSV lists the same
issue under several ids.

Exit 0 when every finding is accepted, 1 for a new advisory, a bad entry or a failed
lookup, 2 for a usage error.

OSV summaries are third-party text and go into the step log, where the runner reads a
line starting with `::` as a command. They pass through `inert` and `annotate` below, the
same handling `check_pin_freshness.py` gives a registry's answer. In the step-summary table
the advisory id and summary go in code spans, so Markdown or HTML in them stays literal, and
an advisory id that is not plain (it is appended to a URL) fails the run.

Standard library only. The network calls are injected so the tests never reach the
network.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REQUIREMENTS_DIR = Path(".github") / "requirements"
ACCEPTED = "advisories-accepted.json"
QUERY_URL = "https://api.osv.dev/v1/querybatch"
VULN_URL = "https://api.osv.dev/v1/vulns/"
BATCH_SIZE = 1000  # OSV answers 400 "too many queries" above this
MAX_ROUNDS = 50  # pagination cap; exceeding it fails closed
MAX_EXPIRY_DAYS = 180
MAX_TEXT = 300


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect, so a request cannot be sent on to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def build_request(url: str, body: dict | None = None) -> urllib.request.Request:
    """The request for one URL: a POST of JSON when a body is given, otherwise a GET."""
    # S310 wants the scheme audited before a URL is opened. This is that audit: every URL
    # is a literal joined with an id, and anything not https is refused first.
    if not url.startswith("https://"):
        raise ValueError(f"refusing to fetch a non-https URL: {url}")
    headers = {"User-Agent": "check-lock-advisories"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(url, data=data, headers=headers)  # noqa: S310 - https enforced above


def _send(request: urllib.request.Request) -> str:
    opener = urllib.request.build_opener(NoRedirect)
    with opener.open(request, timeout=30) as response:
        return response.read().decode("utf-8")


def fetch(url: str) -> str:
    """GET a URL. Left unexercised by the suite, which would otherwise be on the network."""
    return _send(build_request(url))


def send(url: str, body: dict) -> str:
    """POST a JSON body. Left unexercised for the same reason as `fetch`."""
    return _send(build_request(url, body))


def inert(text: str) -> str:
    """Make outside text safe to print: break the legacy `##[` command marker."""
    return text.replace("##[", "## [")


def clean(value: object) -> str:
    """Third-party text reduced to one bounded line."""
    text = " ".join(str(value).split())
    if len(text) > MAX_TEXT:
        text = text[: MAX_TEXT - 3] + "..."
    return inert(text)


def annotate(level: str, title: str, message: str) -> None:
    """Raise one annotation on stderr, escaped so the text stays on its one line."""
    escaped = inert(message).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::{level} title={title}::{escaped}", file=sys.stderr)


def cell(value: object) -> str:
    return clean(value).replace("|", "\\|")


def code_cell(value: object) -> str:
    """Third-party text as an inline code span, so Markdown and HTML in it stay literal."""
    text = clean(value).replace("`", "").replace("|", "\\|")
    return f"`{text}`" if text else ""


def normalise(name: str) -> str:
    """PEP 503 normalisation, used only to compare names in the accepted list."""
    return re.sub(r"[-_.]+", "-", name).lower()


REQUIREMENT = re.compile(
    r"([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*==\s*([A-Za-z0-9][A-Za-z0-9.!+_-]*)"
)
ADVISORY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}")


def parse_lock(text: str, source: str = "lock") -> list[tuple[str, str, str]]:
    """`(name, version, marker)` per requirement line; hashes and comments are skipped.

    Any other line raises, because a line skipped silently is a package never audited.
    """
    found = []
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped[0] == "#" or stripped.startswith("--hash"):
            continue
        line = raw.rstrip("\\").split(" #", 1)[0].strip()
        requirement, _, marker = line.partition(";")
        match = REQUIREMENT.fullmatch(requirement.strip())
        if not match:
            raise ValueError(f"{source} line {number} is not a name==version pin: {clean(raw)!r}")
        found.append((match.group(1), match.group(2), marker.strip()))
    return found


def collect(directory: Path) -> list[tuple[str, str, str, str]]:
    """`(lock file, name, version, marker)` for every lock in the directory."""
    entries = []
    for path in sorted(directory.glob("*.txt")):
        label = f"{REQUIREMENTS_DIR.as_posix()}/{path.name}"
        for name, version, marker in parse_lock(path.read_text(encoding="utf-8"), label):
            entries.append((label, name, version, marker))
    return entries


def query_ids(entries, post_fn) -> list[list[str]]:
    """The advisory ids OSV lists for each entry, following every page token."""
    ids: list[list[str]] = [[] for _ in entries]
    pending: dict[int, str | None] = {i: None for i in range(len(entries))}
    tokens: dict[int, str | None] = {}
    rounds = 0
    while pending:
        rounds += 1
        if rounds > MAX_ROUNDS:
            raise RuntimeError(f"OSV pagination did not finish within {MAX_ROUNDS} rounds")
        indices = sorted(pending)
        pending = {}
        for start in range(0, len(indices), BATCH_SIZE):
            chunk = indices[start : start + BATCH_SIZE]
            queries = []
            for i in chunk:
                _, name, version, _ = entries[i]
                query = {"package": {"name": name, "ecosystem": "PyPI"}, "version": version}
                if tokens.get(i):
                    query["page_token"] = tokens[i]
                queries.append(query)
            results = json.loads(post_fn(QUERY_URL, {"queries": queries})).get("results")
            if not isinstance(results, list) or len(results) != len(chunk):
                raise ValueError("OSV returned a different number of results than queries")
            for i, result in zip(chunk, results, strict=True):
                if not isinstance(result, dict):
                    raise ValueError("OSV returned a result that is not an object")
                for vuln in result.get("vulns", []):
                    vid = vuln["id"] if isinstance(vuln, dict) else None
                    if not isinstance(vid, str) or not ADVISORY_ID.fullmatch(vid):
                        raise ValueError(f"OSV returned an unusable advisory id: {clean(vid)!r}")
                    ids[i].append(vid)
                token = result.get("next_page_token")
                if token:
                    pending[i] = token
        tokens = dict(pending)
    return ids


def load_accepted(root: Path, today: dt.date) -> tuple[list[dict], int]:
    """The valid entries, and how many problems were found with the file."""
    path = root / REQUIREMENTS_DIR / ACCEPTED
    if not path.is_file():
        return [], 0
    problems = 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as err:
        annotate("error", "Accepted list unreadable", f"{ACCEPTED}: {err!r}")
        return [], 1
    if not isinstance(data, list):
        annotate("error", "Accepted list invalid", f"{ACCEPTED} must be a JSON list")
        return [], 1
    valid = []
    for n, item in enumerate(data):
        label = f"{ACCEPTED} entry {n}"
        if not isinstance(item, dict):
            annotate("error", "Accepted entry invalid", f"{label} is not an object")
            problems += 1
            continue
        missing = [k for k in ("id", "package", "reason", "expires") if not _text(item.get(k))]
        if missing:
            annotate("error", "Accepted entry invalid", f"{label} lacks {', '.join(missing)}")
            problems += 1
            continue
        try:
            expires = dt.date.fromisoformat(item["expires"].strip())
        except ValueError:
            annotate("error", "Accepted entry invalid", f"{label} has no ISO expires date")
            problems += 1
            continue
        if expires < today:
            annotate(
                "error",
                "Accepted entry expired",
                f"{label} ({clean(item['id'])}) expired {expires}",
            )
            problems += 1
            continue
        if (expires - today).days > MAX_EXPIRY_DAYS:
            annotate(
                "error",
                "Accepted entry invalid",
                f"{label} expires more than {MAX_EXPIRY_DAYS} days ahead",
            )
            problems += 1
            continue
        valid.append(
            {
                "id": item["id"].strip(),
                "package": normalise(item["package"].strip()),
                "label": item["package"].strip(),
                "reason": item["reason"].strip(),
                "used": False,
            }
        )
    return valid, problems


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check(root: Path, get=None, post=None, today: dt.date | None = None) -> int:
    """Audit every lock. `get` and `post` are resolved at call time so tests can inject."""
    get = fetch if get is None else get
    post = send if post is None else post
    today = dt.date.today() if today is None else today
    directory = root / REQUIREMENTS_DIR
    try:
        entries = collect(directory) if directory.is_dir() else []
    except ValueError as err:
        annotate("error", "Unreadable lock", str(err))
        print("The audit could not run, so no result is claimed.")
        return 1
    if not entries:
        print(f"no requirement locks found under {REQUIREMENTS_DIR}", file=sys.stderr)
        return 2

    accepted, problems = load_accepted(root, today)
    try:
        ids = query_ids(entries, post)
        records: dict[str, dict] = {}
        for found in ids:
            for vid in found:
                if vid not in records:
                    record = json.loads(get(VULN_URL + vid))
                    if not isinstance(record, dict):
                        raise ValueError(f"OSV record {clean(vid)} is not an object")
                    records[vid] = record
    except Exception as err:  # noqa: BLE001 - an audit that could not run must report, never raise
        annotate("error", "Advisory lookup failed", f"could not query OSV: {err!r}")
        print("The audit could not run, so no result is claimed.")
        return 1

    rows = []
    new = 0
    for (lock, name, version, _), found in zip(entries, ids, strict=True):
        for vid in sorted(set(found)):
            record = records[vid]
            if record.get("withdrawn"):
                continue
            aliases = record.get("aliases")
            names = (
                {vid} | {a for a in aliases if isinstance(a, str)}
                if isinstance(aliases, list)
                else {vid}
            )
            summary = clean(record.get("summary") or "no summary")
            match = next(
                (a for a in accepted if a["package"] == normalise(name) and a["id"] in names), None
            )
            if match:
                match["used"] = True
                state = f"accepted: {clean(match['reason'])}"
            else:
                state = "**new**"
                new += 1
                annotate(
                    "error",
                    "New advisory",
                    f"{lock}: {name} {version} has {vid}: {summary}",
                )
            rows.append((lock, name, version, vid, summary, state))

    for entry in accepted:
        if not entry["used"]:
            annotate(
                "warning",
                "Accepted entry matches nothing",
                f"{ACCEPTED}: {clean(entry['id'])} for {clean(entry['label'])} "
                "matches no advisory; remove it",
            )

    if rows:
        print("| Lock | Package | Version | Advisory | Summary | State |")
        print("| --- | --- | --- | --- | --- | --- |")
        for row in rows:
            lock, name, version, vid, summary, state = row
            cells = [cell(lock), cell(name), cell(version), code_cell(vid), code_cell(summary)]
            print("| " + " | ".join([*cells, cell(state)]) + " |")
        print()
    if new:
        print(
            f"{new} new advisory(ies) against the locks. Regenerate the lock as its header "
            f"describes, or add a reviewed entry to {ACCEPTED}."
        )
    if not new and not problems:
        print(f"no advisories outstanding across {len(entries)} locked package(s)")
    return 1 if new or problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_lock_advisories", description=__doc__.split("\n", 1)[0]
    )
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
