# Redirect map, host recipes and the replay

Read this at step 2 to test the map and configure the host, and at step 5 to run the
replay. The map lives in the docs repository as `redirects.csv` with the header
`old,new,status`; host configuration is generated from it rather than edited by hand, so
there is one source to review. Pattern rules for the long tail live in a second file,
`patterns.csv`, with the same header; its `old` ends in `/*` and its `new` ends in
`:splat`. Keeping them apart means the concrete checks below never see a path that is not
a file, and the pattern checks below test them on their own terms.

## Contents

- [Table test for the map](#table-test-for-the-map)
- [Host recipes](#host-recipes)
- [The replay](#the-replay)
- [The ledger check](#the-ledger-check)

## Table test for the map

Run before any preview deploy, and in CI on every change to the map.

```python
#!/usr/bin/env python3
"""Check redirects.csv against the new build: python3 check_map.py redirects.csv site/"""
import csv
import sys
from pathlib import Path

map_file, build_dir = sys.argv[1], Path(sys.argv[2])
rows = list(csv.DictReader(open(map_file, encoding="utf-8")))
olds = [r["old"] for r in rows]
errors = []


def built(path):
    clean = path.split("#")[0].split("?")[0].strip("/")
    candidates = [build_dir / clean / "index.html", build_dir / f"{clean}.html", build_dir / clean]
    return any(c.is_file() for c in candidates)


for dup in {o for o in olds if olds.count(o) > 1}:
    errors.append(f"duplicate old path: {dup}")
for r in rows:
    if r["status"] not in ("301", "308", "410"):
        errors.append(f"{r['old']}: status {r['status']} is not permanent")
    if r["status"] == "410":
        continue
    if r["new"].split("#")[0].rstrip("/") in {o.rstrip("/") for o in olds}:
        errors.append(f"{r['old']} -> {r['new']}: target is itself redirected (chain or loop)")
    if r["new"].rstrip("/") in ("", "/index.html"):
        errors.append(f"{r['old']}: redirects to the homepage")
    if not r["new"].startswith("http") and not built(r["new"]):
        errors.append(f"{r['old']} -> {r['new']}: target not in build output")

print("\n".join(errors) or f"ok: {len(rows)} rows")
sys.exit(1 if errors else 0)
```

Also confirm every tier 1 to 3 path from `old-urls.csv` is either still built at the same
path or has a row in `redirects.csv`; a pattern rule does not count for these tiers.

Check `patterns.csv` separately: each `new` with `:splat` removed must be a directory in
the build output, and the replay below must pass for at least one real old path per
pattern, because the replay is what proves the host expands `:splat` as intended.

```bash
set -Eeuo pipefail
tail -n +2 patterns.csv | while IFS=, read -r old new status; do
  dir="site/${new%:splat}"
  [ -d "$dir" ] || { echo "pattern target not built: $new"; exit 1; }
  [[ "$old" == */\* && "$new" == *:splat && "$status" =~ ^30[18]$ ]] \
    || { echo "malformed pattern row: $old,$new,$status"; exit 1; }
done
```

## Host recipes

Generate one of these from `redirects.csv` and `patterns.csv` in the build, concrete rows
first, since hosts apply the first match. Check the host's current
documentation for rule-count limits before the map grows into the thousands; past a
host's file limit, move the bulk to the CDN's bulk-redirect feature.

**Netlify and Cloudflare Pages** read a `_redirects` file at the publish root, one rule per
line:

```text
/guides/setup          /get-started/install     301
/api/v1/*              /reference/v1/:splat     301
```

**nginx**, with the generated map in its own file:

```nginx
map $uri $docs_redirect {
    include /etc/nginx/docs-redirects.map;   # lines like:  /guides/setup /get-started/install;
}
server {
    if ($docs_redirect) {
        return 301 $docs_redirect;
    }
}
```

A map of several thousand rows needs `map_hash_bucket_size` (and sometimes
`map_hash_max_size`) raised in the `http` block, or nginx refuses to start with "could not
build map_hash".

**Apache**: `Redirect permanent /guides/setup /get-started/install` per row, or
`RedirectMatch 301` for a pattern.

**Amazon S3 static website hosting**: routing rules in the bucket's website configuration,
or the `x-amz-website-redirect-location` metadata on an empty object at the old key.
Routing rules have a count limit, so large maps belong in the CDN in front.

**GitHub Pages** has no server-side redirects. The usual workaround is an HTML page at
each old path with an immediate meta refresh and a canonical link to the new URL
(`jekyll-redirect-from` generates these). Search engines generally treat an instant meta
refresh as a permanent redirect, but other clients may not; for a site where inbound links
matter, put a CDN or a host with real redirects in front.

**Normalisation**: decide once whether paths end in a slash and redirect the other form
with a single host rule. Do the same for `.html` suffixes and `index.html`.

## The replay

Run against the preview before launch and against production straight after. Pass
criteria: each path returns 200 directly, or answers its first hop with a 301 or 308 to
the mapped target, which returns 200. The script checks the first hop's status itself, so
a 302 or 307 from a host rule fails for the whole list, not only the ranked top.

Pass the origin being tested as `base`. For a domain move, pass the new origin as the
optional fourth argument `target`, which is where correctly redirected rows should land.
A map `new` value that starts with `http` is used as it stands; any other value is
prefixed with `target`.

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
base="${1:?usage: replay.sh https://old.example.com redirects.csv old-paths.txt [https://new.example.com]}"
map="$2"; paths="$3"; target_origin="${4:-$base}"; fail=0
while IFS= read -r path; do
  read -r code final hops < <(curl -s -o /dev/null --max-redirs 10 -L \
    -w '%{http_code} %{url_effective} %{num_redirects}\n' "$base$path")
  expected=$(awk -F, -v p="$path" '$1 == p {print $2}' "$map")
  if [[ "$expected" == http* ]]; then want="${expected%%#*}"; else want="$target_origin${expected%%#*}"; fi
  if [[ "$code" != 200 ]]; then
    echo "FAIL $code $path"; fail=1
  elif [[ "$path" != / && ( "$final" == "$target_origin/" || "$final" == "$target_origin" ) ]]; then
    echo "HOME $path -> $final"; fail=1
  elif (( hops > 1 )); then
    echo "CHAIN $hops $path -> $final"; fail=1
  elif [[ -n "$expected" && "$final" != "$want" ]]; then
    echo "WRONG $path -> $final (expected $want)"; fail=1
  elif (( hops == 1 )); then
    first=$(curl -s -o /dev/null -w '%{http_code}' "$base$path")
    if [[ "$first" != 301 && "$first" != 308 ]]; then
      echo "TEMPORARY $first $path"; fail=1
    fi
  fi
done < "$paths"
exit "$fail"
```

`--max-redirs` stops a loop; `%{num_redirects}` counts hops and `%{url_effective}` is where
the client ended up. The `TEMPORARY` branch makes a
second request without `-L` for each redirected row and fails unless the first response is
301 or 308. Rows with status 410 are
expected to fail the 200 check; filter them out of `old-paths.txt` and check them
separately for 410. `old-paths.txt` is the `path` column cut from `old-urls.csv`, minus
the rows the map sends to 410, deduplicated with `sort -u` because `old-urls.csv` has one row per
path and fragment. A page that answers 200 but is the homepage, reached by a redirect the map
never listed, is reported as `HOME`: a catch-all that the 200 check alone would pass.

## The ledger check

Commit `published-urls.txt`, one path per line, seeded from `old-urls.csv` and appended
by the build whenever a new page ships. In CI, after the build:

```bash
set -Eeuo pipefail
missing=$(comm -23 <(sort -u published-urls.txt) \
  <(sort -u <(cd site && find . -name '*.html' | sed 's|^\.||; s|/index\.html$|/|') \
           <(cut -d, -f1 redirects.csv | tail -n +2)))
# A path under a pattern's prefix counts as covered; the replay proves the expansion.
while IFS=, read -r old _ _; do
  prefix="${old%\*}"
  missing=$(printf '%s\n' "$missing" | grep -v -F -x -e '' | grep -v "^${prefix}" || true)
done < <(tail -n +2 patterns.csv)
[ -z "$missing" ] || { printf '%s\n' "$missing"; exit 1; }
```

Any output is a URL that was once published and now neither exists nor redirects, and the
build fails. Adjust the `sed` expression to the site's path style so built paths and ledger
paths compare like for like.
