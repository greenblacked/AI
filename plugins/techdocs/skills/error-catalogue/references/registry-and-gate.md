# Registry and CI gate

Read this when creating the error registry or wiring the check into CI. The registry is
the single source: constants are generated from it, pages are checked against it, and its
own history is what enforces that a code never changes meaning or comes back.

## Contents

- [Registry schema](#registry-schema)
- [Generating constants](#generating-constants)
- [The check script](#the-check-script)
- [Running it in CI](#running-it-in-ci)
- [What the script cannot see](#what-the-script-cannot-see)

## Registry schema

JSON keeps the check on the standard library. One file, for example
`errors/registry.json` in the product repository:

```json
{
  "namespaces": {
    "BIL": "billing-team",
    "AUTH": "identity-team"
  },
  "codes": [
    {
      "code": "BIL-1042",
      "summary": "The card issuer declined the payment",
      "owner": "billing-team",
      "retryable": false,
      "status": "active",
      "since": "4.2.0"
    },
    {
      "code": "BIL-1007",
      "summary": "Payment declined (legacy, unspecified reason)",
      "owner": "billing-team",
      "status": "retired",
      "since": "3.0.0",
      "retired_in": "4.2.0",
      "replaced_by": "BIL-1042"
    }
  ]
}
```

| Field | Rule |
| --- | --- |
| `code` | Namespace prefix from `namespaces`, then the identifier; unique and permanent |
| `summary` | One line in the reader's terms; becomes the page title after the code |
| `owner` | A team, not a person |
| `retryable` | `true` or `false`; required unless retired |
| `status` | `active`, `deprecated` or `retired`, and only ever moves in that direction |
| `since`, `retired_in` | The versions that introduced and retired it, so a reader on an old release can tell which applies |
| `replaced_by` | For a retired code, where its readers should go now |

Allocate the next identifier in a namespace as one more than the highest ever used,
retired codes included, so a retired number is never handed out again. Two open pull
requests can both take the same next number; the duplicate check catches that only when the
job runs on the merge result, so run it on the merge ref and in the merge queue, and the
second pull request to land rebases and takes the following number.

## Generating constants

Generate one constants file per language from the registry in the build, and have throw
sites reference the constant rather than a string literal. The search for a code is then
exact, a typo fails to compile instead of shipping an unknown code, and a retired code can
be removed from the generated file so that new uses fail at build time. Exclude the
generated file from the source scan below, since it lists every code by construction.

## The check script

The default settings assume the numbered `PREFIX-NNNN` scheme. For readable codes such as
`billing.card_declined`, register the namespace (`billing`) and pass `--separator .`, which
changes the namespace check. The script then requires `--pattern`: a namespace is usually
also a module name, so a default that matched `billing.charge(...)` or `import billing.models`
would report ordinary code as unregistered codes. Match the quoted form instead, for
example `--pattern '"((?:billing|auth)\.[a-z][a-z0-9_]*)"'`; with one capture group the
script uses the group, so the quotes are not part of the code.

Standard library only, so it runs on a bare interpreter in any CI image. Save it in the
product repository, for example as `tools/check_error_catalogue.py`.

```python
"""Fail when the error registry, the source and the error pages disagree."""

import argparse
import json
import re
import sys
from pathlib import Path

STATUSES = ("active", "deprecated", "retired")
ORDER = {s: i for i, s in enumerate(STATUSES)}


def load(path, errors):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    registry = {}
    for entry in data["codes"]:
        if entry["code"] in registry:
            errors.append(f"{entry['code']}: listed twice in {path}")
        registry[entry["code"]] = entry
    return registry, data["namespaces"]


def codes_in_source(roots, pattern, excluded):
    found = {}
    for root in roots:
        for path in Path(root).rglob("*"):
            if not path.is_file() or path in excluded:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for code in pattern.findall(text):
                found.setdefault(code, str(path))
    return found


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", required=True)
    p.add_argument("--pages", required=True, help="directory holding <CODE>.md")
    p.add_argument("--src", required=True, nargs="+")
    p.add_argument(
        "--pattern",
        help="regex for a code; default is built from the registered namespaces",
    )
    p.add_argument(
        "--separator",
        default="-",
        help="between namespace and identifier: '-' for BIL-1042, '.' for billing.card_declined",
    )
    p.add_argument("--exclude", nargs="*", default=[], help="generated files")
    p.add_argument("--base-registry", help="the registry as it is on the base branch")
    args = p.parse_args()

    errors = []
    registry, namespaces = load(args.registry, errors)

    for code, entry in registry.items():
        if code.split(args.separator)[0] not in namespaces:
            errors.append(f"{code}: namespace not registered")
        if entry.get("status") not in STATUSES:
            errors.append(f"{code}: status must be one of {', '.join(STATUSES)}")
        if (
            not isinstance(entry.get("retryable"), bool)
            and entry.get("status") != "retired"
        ):
            errors.append(f"{code}: retryable must be true or false")

    # Compared as Path objects so `./src/x.ts` and `src/x.ts` name the same file.
    excluded = {Path(p) for p in args.exclude}
    # Built from the namespaces so SHA-256 or ISO-8601 in a comment is not read as a code.
    # The cost: a code with an unregistered prefix is not seen in source; pass --pattern
    # to widen it.
    names = "|".join(map(re.escape, namespaces))
    sep = re.escape(args.separator)
    tail = "[0-9]{3,5}"  # numbered codes only; readable codes supply --pattern
    if not args.pattern and args.separator != "-":
        p.error("--pattern is required with a separator other than '-'; "
                "match quoted string literals so billing.charge() is not read as a code")
    pattern = args.pattern or rf"\b(?:{names}){sep}{tail}\b"
    in_source = codes_in_source(args.src, re.compile(pattern), excluded)
    for code, where in sorted(in_source.items()):
        if code not in registry:
            errors.append(f"{code}: used in {where} but not in the registry")
        elif registry[code].get("status") == "retired":
            errors.append(f"{code}: retired but still used in {where}")

    for root in args.src:
        # A missing root scans nothing and would pass every source check.
        if not Path(root).is_dir():
            errors.append(f"--src {root}: not a directory, so no source was scanned")

    # An index or README page is navigation, not the page of a code.
    pages = {
        path.stem
        for path in Path(args.pages).glob("*.md")
        if path.stem.lower() not in ("index", "readme")
    }
    for code in sorted(set(registry) - pages):
        errors.append(f"{code}: in the registry with no page")
    for code in sorted(pages - set(registry)):
        errors.append(f"{code}: page exists for a code the registry does not have")

    if args.base_registry:
        base, _ = load(args.base_registry, errors)
        for code, old in sorted(base.items()):
            new = registry.get(code)
            if new is None:
                errors.append(
                    f"{code}: removed from the registry; mark it retired instead"
                )
            elif ORDER.get(new.get("status"), -1) < ORDER.get(old.get("status"), -1):
                errors.append(
                    f"{code}: status moved back from {old['status']} to {new['status']}"
                )

    for line in errors:
        print(f"error: {line}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

It fails, printing one line per problem, when a code used in source is missing from the
registry or retired, when any registry code lacks a page, when a page has no registry
entry, when a code is listed twice, and, given the base branch's registry, when a code has
been removed or its status has moved backwards.

## Running it in CI

Read the base registry from the merge commit's first parent and pass it in, so the
immutability checks run on every pull request. The checkout needs `fetch-depth: 2` and
`persist-credentials: false`; the first parent is the base this merge commit was built on,
so a code added to main afterwards, or a re-run next week, cannot look removed, and no
fetch or credential is needed:

```bash
set -Eeuo pipefail
git show HEAD^1:errors/registry.json > base-registry.json
python3 tools/check_error_catalogue.py \
  --registry errors/registry.json \
  --pages docs/errors \
  --src src \
  --exclude src/generated/error_codes.ts \
  --base-registry base-registry.json
```

Run it on the pull request's merge commit, which is what `pull_request` checks out by
default (`HEAD^1` is the base only there; a merge queue's merge commit works the same
way). On the bare head of a branch that has not been rebased, a code added to the base
since the branch point looks removed, and the check fails for a change the author never made.

When the registry does not yet exist on the base branch, the first pull request that adds
it runs without `--base-registry`. Make the job a required check, so a pull request that
adds a throw site without a page cannot merge.

## What the script cannot see

- **A changed meaning under the same code.** Rewording a summary may be a clarification
  or a new condition; only a person can tell. Route registry changes to the docs owner
  through `CODEOWNERS`.
- **Codes built at runtime.** A code assembled from parts never matches the pattern. Ban
  that in review; codes come from the generated constants.
- **Codes thrown by dependencies.** Wrap them at the boundary into a code you own, and
  document the wrapper code.
- **Page quality.** The gate proves a page exists, not that its fix works. That is the
  job of the page review before merge.
