#!/usr/bin/env bash
# Confirm a deployed catalogue is the version just uploaded.
#
# No token and no Wrangler: curl and python3 only, so this can run in a step that
# does not hold the Cloudflare credential. version.txt is retried because a new
# workers.dev host can take a few seconds to answer. The other paths are required
# once that one has, since they were uploaded in the same version.
set -Eeuo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: smoke_site.sh <https-url> <version> <marketplace-name>" >&2
  exit 2
fi

url=$1
version=$2
market=$3
url=${url%/}

case "$url" in
  https://[a-zA-Z0-9.-]*) ;;
  *)
    echo "smoke url must be https and a hostname" >&2
    exit 1
    ;;
esac

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

fetched=0
attempt=1
while [ "$attempt" -le 15 ]; do
  if curl -fsS --max-time 20 -o "$tmp" "$url/version.txt"; then
    fetched=1
    break
  fi
  sleep 2
  attempt=$((attempt + 1))
done
if [ "$fetched" -ne 1 ]; then
  echo "version.txt did not answer at $url" >&2
  exit 1
fi

got=$(tr -d '\r' <"$tmp" | head -n 1)
if [ "$got" != "$version" ]; then
  echo "version.txt is '$got', expected '$version'" >&2
  exit 1
fi

curl -fsS --max-time 20 -o "$tmp" "$url/marketplace.json"
python3 - "$tmp" "$market" <<'PY'
import json
import sys

path, expected = sys.argv[1], sys.argv[2]
name = json.load(open(path, encoding="utf-8")).get("name")
if name != expected:
    print(f"marketplace name is {name!r}, expected {expected!r}", file=sys.stderr)
    raise SystemExit(1)
PY

curl -fsS --max-time 20 -o /dev/null "$url/"
curl -fsS --max-time 60 -o "$tmp" "$url/portable-skills.zip"
python3 - "$tmp" <<'PY'
import sys

magic = open(sys.argv[1], "rb").read(2)
if magic != b"PK":
    print("portable-skills.zip is not a zip", file=sys.stderr)
    raise SystemExit(1)
PY
