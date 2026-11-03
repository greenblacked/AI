"""Tests for scripts/check_lock_advisories.py, through injected fetchers only.

Nothing here reaches the network: the script takes `get` and `post` callables, and each
test hands it a table, the way the pin-freshness tests do.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import urllib.error
from pathlib import Path

import pytest

from tests.conftest import REPO, load_script

advisories = load_script("check_lock_advisories.py")

TODAY = dt.date(2026, 11, 3)

LOCK = """\
# header comment
#   uv export --no-dev
certifi==2026.10.18 \\
    --hash=sha256:aaaa \\
    --hash=sha256:bbbb
colorama==0.4.6 ; sys_platform == 'win32' \\
    --hash=sha256:cccc
Some_Pkg==1.0 \\
    --hash=sha256:dddd
"""


def make_root(tmp_path: Path, locks: dict[str, str] | None = None, accepted=None) -> Path:
    req = tmp_path / ".github" / "requirements"
    req.mkdir(parents=True)
    for name, text in (locks if locks is not None else {"a.txt": LOCK}).items():
        (req / name).write_text(text, encoding="utf-8")
    if accepted is not None:
        (req / "advisories-accepted.json").write_text(json.dumps(accepted), encoding="utf-8")
    return tmp_path


class Osv:
    """A stand-in for api.osv.dev: vulns by (name, version), records by id."""

    def __init__(self, vulns=None, records=None):
        self.vulns = vulns or {}
        self.records = records or {}
        self.posts: list[dict] = []
        self.gets: list[str] = []

    def post(self, url, body):
        assert url == "https://api.osv.dev/v1/querybatch"
        self.posts.append(body)
        results = []
        for q in body["queries"]:
            assert q["package"]["ecosystem"] == "PyPI"
            ids = self.vulns.get((q["package"]["name"], q["version"]), [])
            results.append(
                {"vulns": [{"id": i, "modified": "2026-01-01T00:00:00Z"} for i in ids]}
                if ids
                else {}
            )
        return json.dumps({"results": results})

    def get(self, url):
        self.gets.append(url)
        prefix = "https://api.osv.dev/v1/vulns/"
        assert url.startswith(prefix)
        record = self.records.get(url[len(prefix) :])
        if record is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return json.dumps(record)


def run(root, osv, today=TODAY):
    return advisories.check(root, get=osv.get, post=osv.post, today=today)


def record(vid, summary="bad thing", aliases=(), **extra):
    return {
        "id": vid,
        "modified": "2026-01-01T00:00:00Z",
        "summary": summary,
        "aliases": list(aliases),
        **extra,
    }


def entry(**over):
    base = {
        "id": "GHSA-aaaa-bbbb-cccc",
        "package": "certifi",
        "reason": "not reachable",
        "expires": "2027-01-01",
    }
    return {**base, **over}


# --- parsing -----------------------------------------------------------------------


def test_parse_reads_names_versions_and_markers_and_skips_hashes_and_comments():
    assert advisories.parse_lock(LOCK) == [
        ("certifi", "2026.10.18", ""),
        ("colorama", "0.4.6", "sys_platform == 'win32'"),
        ("Some_Pkg", "1.0", ""),
    ]


def test_a_win32_only_package_is_still_queried(tmp_path, capsys):
    osv = Osv()
    assert run(make_root(tmp_path), osv) == 0
    queried = {(q["package"]["name"], q["version"]) for q in osv.posts[0]["queries"]}
    assert ("colorama", "0.4.6") in queried
    assert ("Some_Pkg", "1.0") in queried


# --- findings ----------------------------------------------------------------------


def test_a_new_advisory_fails_and_names_file_package_and_id(tmp_path, capsys):
    osv = Osv({("certifi", "2026.10.18"): ["GHSA-x"]}, {"GHSA-x": record("GHSA-x", "oh no")})
    assert run(make_root(tmp_path), osv) == 1
    captured = capsys.readouterr()
    assert "::error" in captured.err
    for word in ("a.txt", "certifi", "2026.10.18", "GHSA-x", "oh no"):
        assert word in captured.err
    assert "GHSA-x" in captured.out


def test_summary_text_cannot_start_a_command_or_break_the_table(tmp_path, capsys):
    nasty = "line\n::error::forged ##[add-mask]x 100% | col"
    osv = Osv({("certifi", "2026.10.18"): ["GHSA-x"]}, {"GHSA-x": record("GHSA-x", nasty)})
    assert run(make_root(tmp_path), osv) == 1
    captured = capsys.readouterr()
    for stream in (captured.out, captured.err):
        assert "##[" not in stream
        for line in stream.splitlines():
            assert not line.startswith("::") or line.startswith("::error title=")
    assert len(captured.err.splitlines()) == 1
    assert "100%25" in captured.err and "line ::error" in captured.err
    table_rows = [ln for ln in captured.out.splitlines() if "GHSA-x" in ln]
    assert len(table_rows) == 1
    assert "col" in table_rows[0] and "\\|" in table_rows[0]


def test_a_clean_audit_exits_zero(tmp_path, capsys):
    assert run(make_root(tmp_path), Osv()) == 0
    assert "no advisories" in capsys.readouterr().out


def test_a_withdrawn_advisory_is_ignored(tmp_path):
    osv = Osv(
        {("certifi", "2026.10.18"): ["GHSA-x"]},
        {"GHSA-x": record("GHSA-x", withdrawn="2026-02-02T00:00:00Z")},
    )
    assert run(make_root(tmp_path), osv) == 0


def test_the_same_advisory_is_fetched_once(tmp_path):
    locks = {"a.txt": LOCK, "b.txt": LOCK}
    osv = Osv({("certifi", "2026.10.18"): ["GHSA-x"]}, {"GHSA-x": record("GHSA-x")})
    assert run(make_root(tmp_path, locks), osv) == 1
    assert osv.gets == ["https://api.osv.dev/v1/vulns/GHSA-x"]


# --- the accepted list -------------------------------------------------------------


def found(tmp_path, accepted, aliases=("PYSEC-1",)):
    osv = Osv(
        {("certifi", "2026.10.18"): ["PYSEC-1"]},
        {"PYSEC-1": record("PYSEC-1", aliases=["GHSA-aaaa-bbbb-cccc", *aliases])},
    )
    return run(make_root(tmp_path, accepted=accepted), osv)


def test_an_accepted_advisory_passes(tmp_path):
    assert found(tmp_path, [entry(id="PYSEC-1")]) == 0


def test_an_alias_accepts_the_advisory(tmp_path):
    assert found(tmp_path, [entry()]) == 0


def test_the_package_name_is_compared_normalised(tmp_path):
    assert found(tmp_path, [entry(package="CERTIFI")]) == 0


def test_an_entry_for_another_package_does_not_accept(tmp_path, capsys):
    assert found(tmp_path, [entry(package="other")]) == 1
    assert "other" in capsys.readouterr().err  # reported as stale


def test_an_expired_entry_fails(tmp_path, capsys):
    assert found(tmp_path, [entry(expires="2026-11-02")]) == 1
    assert "expired" in capsys.readouterr().err


def test_an_entry_expiring_today_is_still_valid(tmp_path):
    assert found(tmp_path, [entry(expires="2026-11-03")]) == 0


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_an_entry_without_a_reason_fails(tmp_path, reason):
    assert found(tmp_path, [entry(reason=reason)]) == 1


def test_an_expiry_beyond_180_days_fails(tmp_path):
    far = (TODAY + dt.timedelta(days=181)).isoformat()
    assert found(tmp_path, [entry(expires=far)]) == 1


def test_an_expiry_at_180_days_is_allowed(tmp_path):
    edge = (TODAY + dt.timedelta(days=180)).isoformat()
    assert found(tmp_path, [entry(expires=edge)]) == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"id": "x"},
        {"id": "x", "package": "p", "reason": "r", "expires": "not-a-date"},
        "string",
    ],
)
def test_a_malformed_entry_fails(tmp_path, bad):
    assert found(tmp_path, [bad]) == 1


def test_a_non_list_accepted_file_fails(tmp_path):
    assert found(tmp_path, {"id": "x"}) == 1


def test_unparseable_accepted_file_fails(tmp_path):
    root = make_root(tmp_path)
    (root / ".github/requirements/advisories-accepted.json").write_text("{", encoding="utf-8")
    assert run(root, Osv()) == 1


def test_a_stale_entry_warns_but_passes(tmp_path, capsys):
    root = make_root(tmp_path, accepted=[entry(id="GHSA-gone")])
    assert run(root, Osv()) == 0
    captured = capsys.readouterr()
    assert "::warning" in captured.err
    assert "GHSA-gone" in captured.err


def test_the_accepted_file_is_not_read_as_a_lock(tmp_path):
    root = make_root(tmp_path, accepted=[])
    osv = Osv()
    assert run(root, osv) == 0
    assert len(osv.posts[0]["queries"]) == 3


# --- the lookup --------------------------------------------------------------------


def test_queries_are_batched_to_the_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(advisories, "BATCH_SIZE", 2)
    osv = Osv()
    assert run(make_root(tmp_path), osv) == 0
    assert [len(p["queries"]) for p in osv.posts] == [2, 1]


def test_a_next_page_token_is_followed_even_with_no_vulns(tmp_path):
    class Paged(Osv):
        def post(self, url, body):
            self.posts.append(body)
            out = []
            for q in body["queries"]:
                if q["package"]["name"] != "certifi":
                    out.append({})
                elif "page_token" not in q:
                    out.append({"next_page_token": "TOK1"})  # timeout: token and nothing else
                elif q.get("page_token") == "TOK1":
                    out.append(
                        {"vulns": [{"id": "GHSA-x", "modified": "m"}], "next_page_token": "TOK2"}
                    )
                else:
                    assert q.get("page_token") == "TOK2"
                    out.append({"vulns": [{"id": "GHSA-y", "modified": "m"}]})
            return json.dumps({"results": out})

    osv = Paged(records={"GHSA-x": record("GHSA-x"), "GHSA-y": record("GHSA-y")})
    assert run(make_root(tmp_path), osv) == 1
    assert sorted(osv.gets) == [
        "https://api.osv.dev/v1/vulns/GHSA-x",
        "https://api.osv.dev/v1/vulns/GHSA-y",
    ]
    # Only the paged query is re-sent, unchanged but for the token.
    assert [len(p["queries"]) for p in osv.posts] == [3, 1, 1]


def test_pagination_that_never_ends_fails_closed(tmp_path):
    def post(url, body):
        return json.dumps({"results": [{"next_page_token": "T"} for _ in body["queries"]]})

    assert advisories.check(make_root(tmp_path), get=Osv().get, post=post, today=TODAY) == 1


def test_a_short_result_list_fails(tmp_path):
    def post(url, body):
        return json.dumps({"results": []})

    assert advisories.check(make_root(tmp_path), get=Osv().get, post=post, today=TODAY) == 1


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("u", 500, "Server Error", {}, None),
        TimeoutError("timed out"),
        urllib.error.URLError("down"),
    ],
)
def test_a_transport_failure_exits_one_on_the_batch(tmp_path, capsys, failure):
    def post(url, body):
        raise failure

    assert advisories.check(make_root(tmp_path), get=Osv().get, post=post, today=TODAY) == 1
    assert "::error" in capsys.readouterr().err


@pytest.mark.parametrize("body", ["not json", "[]", '{"results": "x"}', '{"results": [1, 2, 3]}'])
def test_an_unparseable_batch_response_exits_one(tmp_path, body):
    assert (
        advisories.check(make_root(tmp_path), get=Osv().get, post=lambda u, b: body, today=TODAY)
        == 1
    )


def test_a_record_that_cannot_be_fetched_fails(tmp_path):
    osv = Osv({("certifi", "2026.10.18"): ["GHSA-x"]}, {})
    assert run(make_root(tmp_path), osv) == 1


def test_a_record_with_invalid_json_fails(tmp_path):
    osv = Osv({("certifi", "2026.10.18"): ["GHSA-x"]})
    osv.get = lambda url: "{"
    assert run(make_root(tmp_path), osv) == 1


def test_a_record_that_is_not_an_object_fails(tmp_path):
    osv = Osv({("certifi", "2026.10.18"): ["GHSA-x"]})
    osv.get = lambda url: "[]"
    assert run(make_root(tmp_path), osv) == 1


# --- usage -------------------------------------------------------------------------


def test_an_empty_requirements_directory_is_a_usage_error(tmp_path):
    assert run(make_root(tmp_path, locks={}), Osv()) == 2


def test_a_missing_requirements_directory_is_a_usage_error(tmp_path):
    assert run(tmp_path, Osv()) == 2


def test_main_exits_two_on_an_empty_directory(tmp_path):
    make_root(tmp_path, locks={})
    assert advisories.main([str(tmp_path)]) == 2


# --- requests ----------------------------------------------------------------------


def test_build_request_refuses_a_non_https_url():
    with pytest.raises(ValueError):
        advisories.build_request("http://api.osv.dev/v1/querybatch")
    with pytest.raises(ValueError):
        advisories.build_request("file:///etc/passwd")


def test_build_request_sends_json_with_a_user_agent():
    req = advisories.build_request("https://api.osv.dev/v1/querybatch", {"queries": []})
    assert req.get_method() == "POST"
    assert req.data == b'{"queries": []}'
    assert req.get_header("Content-type") == "application/json"
    assert req.get_header("User-agent")
    assert advisories.build_request("https://api.osv.dev/v1/vulns/X").get_method() == "GET"


def test_redirects_are_refused():
    handler = advisories.NoRedirect()
    with pytest.raises(urllib.error.HTTPError):
        handler.redirect_request(
            advisories.build_request("https://api.osv.dev/v1/vulns/X"),
            None,
            302,
            "Found",
            {},
            "https://evil.example/",
        )


# --- the real repository -----------------------------------------------------------


def test_the_repositorys_accepted_list_is_valid_json_list():
    path = REPO / ".github" / "requirements" / "advisories-accepted.json"
    assert isinstance(json.loads(path.read_text(encoding="utf-8")), list)


def test_the_repositorys_locks_all_parse():
    for path in sorted((REPO / ".github" / "requirements").glob("*.txt")):
        assert advisories.parse_lock(path.read_text(encoding="utf-8")), path.name


# --- the workflow job --------------------------------------------------------------


def _job() -> str:
    text = (REPO / ".github" / "workflows" / "scheduled.yml").read_text(encoding="utf-8")
    start = text.index("\n  dependency-advisories:")
    rest = text[start + 1 :]
    match = re.search(r"\n  [a-z][a-z-]*:\n", rest[3:])
    return rest if not match else rest[: match.start() + 3]


def test_the_job_is_least_privilege_and_bounded():
    job = _job()
    assert "permissions:\n      contents: read" in job
    assert "timeout-minutes: 10" in job
    assert "persist-credentials: false" in job
    assert "secrets." not in job and "GH_TOKEN" not in job


def test_the_job_pins_its_actions_to_the_shas_the_file_already_uses():
    job = _job()
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1" in job
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97  # v7.0.0" in job


def test_the_job_has_no_expression_inside_run():
    job = _job()
    run_block = job[job.index("run: |") :]
    assert "${{" not in run_block
    assert "set -Eeuo pipefail" in run_block
    assert "scripts/check_lock_advisories.py" in run_block
    assert '"$GITHUB_STEP_SUMMARY"' in run_block
