#!/usr/bin/env python3
"""Read the workers.dev URL out of a Wrangler deploy or preview log.

Wrangler appends one JSON object per line when ``WRANGLER_OUTPUT_FILE_PATH`` is set.
The line with ``"type": "deploy"`` carries ``targets``, the URLs that version is
served at. This prints ``url=`` and, when Wrangler sent one, ``version_id=`` in the
form ``GITHUB_OUTPUT`` expects, and nothing else on stdout.

A target is accepted only as ``https`` on a ``workers.dev`` host, with no user, port,
path or query. Anything else is dropped. When several targets qualify, the one with
the fewest labels wins: that is ``name.account.workers.dev``, not a longer preview
host. A missing or unreadable URL is an error, because a deploy that succeeded and
then left no address cannot be smoke-tested.

``--preview`` reads the last ``"type": "preview"`` line instead and takes its
``preview_urls``. It prints ``url=`` for the workers.dev Preview URL, when there is
one, and ``custom_url=`` for the Preview's host under the production custom domain,
when Wrangler reported one. A Preview URL is accepted under the same https rules, on
a ``workers.dev`` host or on ``ai.szolotov.com`` or one of its subdomains. Wrangler
only reports the custom host once that domain is enabled for Preview traffic, so a
missing ``custom_url`` is for the caller to turn into an error, not for this script.
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
# The production custom domain. A Preview is served at <name>.<this domain> once the
# domain's route has previews_enabled, so a host is trusted only at or below it.
CUSTOM_DOMAIN = "ai.szolotov.com"
STAGE_URL = f"https://stage.{CUSTOM_DOMAIN}"
VERSION_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _acceptable(url: object) -> str | None:
    if not isinstance(url, str) or HOST_RE.fullmatch(url) is None:
        return None
    if not url.endswith(".workers.dev"):
        return None
    return url


def _acceptable_preview(url: object) -> str | None:
    if not isinstance(url, str) or HOST_RE.fullmatch(url) is None:
        return None
    host = url.removeprefix("https://")
    if host.endswith(".workers.dev") or host == CUSTOM_DOMAIN or host.endswith("." + CUSTOM_DOMAIN):
        return url
    return None


def parse_preview(text: str) -> tuple[str, str]:
    """``(workers_dev_url, custom_url)`` from the last preview line; either may be empty.

    ``custom_url`` is the stage host when it is reported, else the shortest other host
    at or below the custom domain, so the caller can say which host it got instead.
    """
    urls: list[str] = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict) or item.get("type") != "preview":
            continue
        reported = item.get("preview_urls")
        urls = []
        if isinstance(reported, list):
            for entry in reported:
                url = _acceptable_preview(entry)
                if url is not None:
                    urls.append(url)
    if not urls:
        raise SystemExit("wrangler preview reported no https workers.dev or custom-domain URL")
    urls.sort(key=lambda url: (url.count("."), len(url)))
    workers_dev = next((url for url in urls if url.endswith(".workers.dev")), "")
    custom = [url for url in urls if not url.endswith(".workers.dev")]
    chosen = STAGE_URL if STAGE_URL in custom else (custom[0] if custom else "")
    return workers_dev, chosen


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
    parser.add_argument(
        "--preview", action="store_true", help="read a wrangler preview log, not a deploy log"
    )
    parser.add_argument("path", type=Path, help="the WRANGLER_OUTPUT_FILE_PATH file")
    args = parser.parse_args(argv)
    if not args.path.is_file():
        print(f"no wrangler output at {args.path}", file=sys.stderr)
        return 1
    if args.preview:
        url, custom_url = parse_preview(args.path.read_text(encoding="utf-8"))
        if url:
            sys.stdout.write(f"url={url}\n")
        if custom_url:
            sys.stdout.write(f"custom_url={custom_url}\n")
        return 0
    url, version_id = parse(args.path.read_text(encoding="utf-8"))
    sys.stdout.write(f"url={url}\n")
    if version_id:
        sys.stdout.write(f"version_id={version_id}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
