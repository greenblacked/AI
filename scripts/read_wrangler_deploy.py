#!/usr/bin/env python3
"""Read the workers.dev URL out of a Wrangler deploy log.

Wrangler appends one JSON object per line when ``WRANGLER_OUTPUT_FILE_PATH`` is set.
The line with ``"type": "deploy"`` carries ``targets``, the URLs that version is
served at. This prints ``url=`` and, when Wrangler sent one, ``version_id=`` in the
form ``GITHUB_OUTPUT`` expects, and nothing else on stdout.

A target is accepted only as ``https`` on a ``workers.dev`` host, with no user, port,
path or query. Anything else is dropped. When several targets qualify, the one with
the fewest labels wins: that is ``name.account.workers.dev``, not a longer preview
host. A missing or unreadable URL is an error, because a deploy that succeeded and
then left no address cannot be smoke-tested.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# One label is 1-63 characters, cannot start or end with a hyphen. The host must be
# at least three labels so a bare https://workers.dev cannot pass.
HOST_RE = re.compile(
    r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?){2,}$"
)
VERSION_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _acceptable(url: object) -> str | None:
    if not isinstance(url, str) or HOST_RE.fullmatch(url) is None:
        return None
    if not url.endswith(".workers.dev"):
        return None
    return url


def parse(text: str) -> tuple[str, str]:
    """``(url, version_id)``. ``version_id`` is empty when the line has none we can trust."""
    chosen: str | None = None
    version_id = ""
    for raw in text.splitlines():
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict) or item.get("type") != "deploy":
            continue
        targets = item.get("targets")
        found = []
        if isinstance(targets, list):
            for target in targets:
                url = _acceptable(target)
                if url is not None:
                    found.append(url)
        if not found:
            continue
        # Fewer labels first, then the shorter URL. A preview host is longer.
        found.sort(key=lambda url: (url.count("."), len(url)))
        chosen = found[0]
        candidate = item.get("version_id")
        version_id = (
            candidate if isinstance(candidate, str) and VERSION_ID_RE.fullmatch(candidate) else ""
        )
    if chosen is None:
        raise SystemExit("wrangler deploy reported no https workers.dev target")
    return chosen, version_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="read_wrangler_deploy", description=__doc__.split("\n", 1)[0]
    )
    parser.add_argument("path", type=Path, help="the WRANGLER_OUTPUT_FILE_PATH file")
    args = parser.parse_args(argv)
    if not args.path.is_file():
        print(f"no wrangler output at {args.path}", file=sys.stderr)
        return 1
    url, version_id = parse(args.path.read_text(encoding="utf-8"))
    sys.stdout.write(f"url={url}\n")
    if version_id:
        sys.stdout.write(f"version_id={version_id}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
