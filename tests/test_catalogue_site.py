"""The catalogue site is what a release uploads, so a bad build has to fail here.

The deploy workflow trusts this script to refuse a version that is not a token and to
refuse to delete a directory it did not itself create. Both are silent if they only
hold in the happy path.
"""

from __future__ import annotations

import html
import http.server
import json
import os
import subprocess
import threading
import time
import zipfile
from pathlib import Path

import pytest

from tests.conftest import REPO, load_script

site = load_script("build_catalogue_site.py")


def test_a_mini_repository_builds_a_site(mini_repo, tmp_path):
    manifest_path = mini_repo / ".claude-plugin" / "marketplace.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["description"] = "A <b>catalogue</b>"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "site"
    site.build(mini_repo, output, "  v1.2.3  ")
    assert (output / "version.txt").read_text(encoding="utf-8") == "v1.2.3\n"
    names = sorted(path.name for path in (output / "skills").iterdir())
    assert names == ["alpha.skill", "beta.skill"]
    page = (output / "index.html").read_text(encoding="utf-8")
    assert "alpha" in page and "beta" in page
    assert "v1.2.3" in page
    assert "https://github.com/greenblacked/AI" in page
    assert "Made by Serhii Zolotov" in page
    assert ">Black<" in page
    assert "Release <code>" not in page
    assert html.escape("A <b>catalogue</b>") in page
    assert "<b>" not in page
    manifest = json.loads((output / "marketplace.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "mini"
    assert (output / "robots.txt").read_text(encoding="utf-8").startswith("User-agent: *\nAllow:")
    assert (output / ".catalogue-site").is_file()
    assert ".catalogue-site" in (output / ".assetsignore").read_text(encoding="utf-8")
    with zipfile.ZipFile(output / "portable-skills.zip") as bundle:
        assert any(name.endswith("alpha.md") for name in bundle.namelist())
    # A second build replaces the first rather than refusing its own sentinel.
    site.build(mini_repo, output, "v1.2.4", noindex=True)
    assert (output / "version.txt").read_text(encoding="utf-8") == "v1.2.4\n"
    assert "Disallow:" in (output / "robots.txt").read_text(encoding="utf-8")


def test_versions_that_are_not_a_single_token_are_refused(mini_repo, tmp_path):
    for raw in ("", "../etc", "has space", "a" * 81, ".hidden"):
        with pytest.raises(SystemExit):
            site.build(mini_repo, tmp_path / "site", raw)


def test_a_missing_or_nameless_manifest_is_refused(mini_repo, tmp_path):
    manifest = mini_repo / ".claude-plugin" / "marketplace.json"
    manifest.unlink()
    with pytest.raises(SystemExit, match="no marketplace"):
        site.build(mini_repo, tmp_path / "site", "v1")
    manifest.write_text("{", encoding="utf-8")
    with pytest.raises(SystemExit, match="not JSON"):
        site.build(mini_repo, tmp_path / "site", "v1")
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="no string name"):
        site.build(mini_repo, tmp_path / "site", "v1")


def test_the_repository_itself_and_a_foreign_directory_are_not_deleted(mini_repo, tmp_path):
    with pytest.raises(SystemExit, match="repository root"):
        site.build(mini_repo, mini_repo, "v1")
    assert (mini_repo / "LICENSE").is_file()
    foreign = tmp_path / "notes"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit, match="not a previous"):
        site.build(mini_repo, foreign, "v1")
    assert (foreign / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_home_and_a_parent_of_the_repository_are_unsafe(mini_repo):
    assert site.unsafe_output(mini_repo, Path.home()) == "it is the home directory"
    assert "contains it" in site.unsafe_output(mini_repo, mini_repo.parent)


def test_plugins_the_manifest_does_not_name_are_still_listed():
    groups = site._ordered_groups(
        {"plugins": [{"name": "beta"}, "nope", {"name": 1}, {"name": "missing"}]},
        {"alpha": ["a.skill"], "beta": ["b.skill", "a.skill"]},
    )
    assert groups == [("beta", ["a.skill", "b.skill"]), ("alpha", ["a.skill"])]


def test_plugins_that_are_not_a_list_are_still_listed():
    groups = site._ordered_groups({"plugins": "nope"}, {"alpha": ["a.skill"]})
    assert groups == [("alpha", ["a.skill"])]


def test_a_failed_portable_export_is_refused(mini_repo, tmp_path, monkeypatch):
    monkeypatch.setattr(site.export_portable, "export", lambda _root, _exported: 2)
    with pytest.raises(SystemExit, match="portable export failed"):
        site.build(mini_repo, tmp_path / "site", "v1")


def test_the_real_pin_matches_the_lockfile():
    pin = load_script("check_wrangler_pin.py")
    assert pin.problems(REPO, "4.147.0") == []
    assert any("not" in item for item in pin.problems(REPO, "0.0.1"))


def test_a_lockfile_without_an_integrity_is_refused(tmp_path):
    pin = load_script("check_wrangler_pin.py")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "package.json").write_text(
        json.dumps({"dependencies": {"wrangler": "1.2.3"}}), encoding="utf-8"
    )
    (deploy / "package-lock.json").write_text(
        json.dumps({"packages": {"node_modules/wrangler": {"version": "1.2.3"}}}),
        encoding="utf-8",
    )
    found = pin.problems(tmp_path, "1.2.3")
    assert any("integrity" in item for item in found)
    assert pin.problems(tmp_path / "missing", "1.2.3")


def test_a_pin_that_is_not_json_is_refused(tmp_path, capsys):
    pin = load_script("check_wrangler_pin.py")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "package.json").write_text("{", encoding="utf-8")
    (deploy / "package-lock.json").write_text("{}", encoding="utf-8")
    assert any("not JSON" in item for item in pin.problems(tmp_path, "1"))
    (deploy / "package.json").write_text("[]", encoding="utf-8")
    (deploy / "package-lock.json").write_text("[]", encoding="utf-8")
    assert pin.problems(tmp_path, "1")
    assert pin.main(["--version", "0.0.1", str(REPO)]) == 1
    assert "::error::" in capsys.readouterr().err


def test_a_repository_with_no_skills_is_refused(tmp_path):
    root = tmp_path / "empty"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "marketplace.json").write_text('{"name": "x"}\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="no skills"):
        site.build(root, tmp_path / "site", "v1")


def test_mains_report_the_pin_and_the_deploy_url(mini_repo, tmp_path, capsys):
    output = tmp_path / "out"
    assert site.main(["--version", "dev", "--out", str(output), str(mini_repo)]) == 0
    assert "dev" in capsys.readouterr().out
    pin = load_script("check_wrangler_pin.py")
    assert pin.main(["--version", "", str(REPO)]) == 1
    assert pin.main(["--version", "4.147.0", str(REPO)]) == 0
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(
        json.dumps({"type": "deploy", "targets": ["https://greenblacked-ai.account.workers.dev"]})
        + "\n",
        encoding="utf-8",
    )
    assert reader.main([str(log)]) == 0
    assert "url=https://greenblacked-ai.account.workers.dev" in capsys.readouterr().out
    assert reader.main([str(tmp_path / "missing")]) == 1
    version = "12345678-1234-1234-1234-123456789abc"
    text = "\n".join(
        [
            "not json",
            json.dumps({"type": "wrangler-session", "version": 1}),
            json.dumps(
                {
                    "type": "deploy",
                    "targets": [
                        "https://abc.greenblacked-ai.account.workers.dev",
                        "http://greenblacked-ai.account.workers.dev",
                        "https://greenblacked-ai.account.workers.dev/extra",
                        "https://greenblacked-ai.account.workers.dev",
                        "https://example.com",
                    ],
                    "version_id": version,
                }
            ),
        ]
    )
    url, found = reader.parse(text)
    assert url == "https://greenblacked-ai.account.workers.dev"
    assert found == version
    with pytest.raises(SystemExit):
        reader.parse("{}\n")
    # A version id that is not a UUID is dropped rather than written into an output file.
    loose = json.dumps(
        {
            "type": "deploy",
            "targets": ["https://greenblacked-ai.account.workers.dev"],
            "version_id": "not a uuid\nurl=https://evil.example",
        }
    )
    assert reader.parse(loose)[1] == ""


def _preview_line(urls):
    return json.dumps({"type": "preview", "version": 1, "preview_urls": urls}) + "\n"


def test_a_preview_log_reports_the_workers_dev_and_stage_hosts(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(
        "not json\n"
        + _preview_line(["https://old.account.workers.dev"])
        + _preview_line(
            [
                "https://stage-ai.account.workers.dev",
                "https://stage.ai.szolotov.com",
                "https://other.ai.szolotov.com",
            ]
        ),
        encoding="utf-8",
    )
    assert reader.main(["--preview", str(log)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "url=https://stage-ai.account.workers.dev",
        "custom_url=https://stage.ai.szolotov.com",
    ]
    assert reader.parse_preview(log.read_text(encoding="utf-8")) == (
        "https://stage-ai.account.workers.dev",
        "https://stage.ai.szolotov.com",
    )


def test_a_preview_log_without_the_custom_host_leaves_it_empty(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    log = tmp_path / "wrangler.jsonl"
    log.write_text(_preview_line(["https://stage-ai.account.workers.dev"]), encoding="utf-8")
    assert reader.main(["--preview", str(log)]) == 0
    assert capsys.readouterr().out == "url=https://stage-ai.account.workers.dev\n"
    # A different host under the custom domain is reported as such, not as the stage host.
    assert reader.parse_preview(_preview_line(["https://x.ai.szolotov.com"])) == (
        "",
        "https://x.ai.szolotov.com",
    )


def test_a_preview_log_with_no_line_or_no_acceptable_url_is_an_error(tmp_path):
    reader = load_script("read_wrangler_deploy.py")
    deploy_only = json.dumps({"type": "deploy", "targets": ["https://a.b.workers.dev"]})
    with pytest.raises(SystemExit):
        reader.parse_preview(deploy_only + "\n")
    with pytest.raises(SystemExit):
        reader.parse_preview("")
    with pytest.raises(SystemExit):
        reader.parse_preview(json.dumps({"type": "preview", "preview_urls": "x"}))
    # Only the last preview line counts: an earlier good one does not cover a later empty one.
    with pytest.raises(SystemExit):
        reader.parse_preview(_preview_line(["https://a.b.workers.dev"]) + _preview_line([]))
    assert reader.main(["--preview", str(tmp_path / "missing")]) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://stage.ai.szolotov.com",
        "https://user@stage.ai.szolotov.com",
        "https://user:pw@stage.ai.szolotov.com",
        "https://stage.ai.szolotov.com:8443",
        "https://stage.ai.szolotov.com/path",
        "https://stage.ai.szolotov.com/?q=1",
        "https://stage.ai.szolotov.com#frag",
        "https://stage.ai.szolotov.com.evil.com",
        "https://evil.com/stage.ai.szolotov.com",
        "https://notai.szolotov.com",
        "https://stage.szolotov.com",
        "https://szolotov.com",
        "https://workers.dev",
        "https://a.workers.dev.evil.com",
        "https://a.b.workers.dev:443",
        "https://example.com",
        "https://STAGE.ai.szolotov.com",
        "https://a.b.workers.dev\nurl=https://evil.example",
    ],
)
def test_hostile_preview_urls_are_dropped(url):
    reader = load_script("read_wrangler_deploy.py")
    with pytest.raises(SystemExit):
        reader.parse_preview(_preview_line([url]))
    # One hostile entry does not hide a good one next to it.
    good = "https://stage.ai.szolotov.com"
    assert reader.parse_preview(_preview_line([url, good])) == ("", good)


def test_the_deploy_log_keeps_only_a_workers_dev_url(tmp_path, capsys):
    reader = load_script("read_wrangler_deploy.py")
    version = "12345678-1234-1234-1234-123456789abc"
    text = "\n".join(
        [
            "",
            json.dumps({"type": "deploy", "targets": "https://a.b.workers.dev"}),
            json.dumps(
                {
                    "type": "deploy",
                    "targets": ["https://not.a.worker.example", "https://name.account.workers.dev"],
                    "version_id": version,
                }
            ),
        ]
    )
    url, found = reader.parse(text)
    assert url == "https://name.account.workers.dev"
    assert found == version
    log = tmp_path / "wrangler.jsonl"
    log.write_text(text, encoding="utf-8")
    assert reader.main([str(log)]) == 0
    assert f"version_id={version}" in capsys.readouterr().out


def test_one_worker_serves_production_and_previews_on_the_custom_domain():
    config = json.loads((REPO / "deploy" / "wrangler.json").read_text(encoding="utf-8"))
    assert config["name"] == "ai"
    assert config["workers_dev"] is True
    assert config["preview_urls"] is True
    assert config["previews"] == {}
    assert config["routes"] == [
        {"pattern": "ai.szolotov.com", "custom_domain": True, "previews_enabled": True}
    ]
    # No environments remain: a second name would be a second Worker.
    assert "env" not in config


def test_the_stage_branch_uploads_a_preview_and_smokes_the_fixed_host():
    workflow = (REPO / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "--env" not in workflow
    assert "wrangler rollback" not in workflow
    assert "wrangler deploy --config" not in workflow
    deploy = workflow.split("      - name: Upload the stage Preview\n", 1)[1].split(
        "      - name: Smoke-test the stage Preview\n", 1
    )[0]
    assert "wrangler preview --config wrangler.json --name stage" in deploy
    assert "WRANGLER_OUTPUT_FILE_PATH" in deploy
    assert 'read_wrangler_deploy.py" --preview' in deploy
    smoke = workflow.split("      - name: Smoke-test the stage Preview\n", 1)[1]
    assert "stage_url=https://stage.ai.szolotov.com" in smoke
    assert 'urls=("$stage_url")' in smoke
    assert "::error::Wrangler did not report ${stage_url} for this Preview" in smoke
    assert "enable ai.szolotov.com for Preview traffic (docs/ci.md)" in smoke
    assert 'if [ -n "$CONFIGURED_URL" ]' in smoke
    assert 'scripts/smoke_site.sh "$target" "$VERSION" greenblacked-ai' in smoke


def test_production_smokes_the_custom_domain_without_a_deploy_url():
    workflow = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "--env" not in workflow
    smoke = workflow.split("      - name: Smoke-test the production Worker\n", 1)[1].split(
        "      - name: Roll back the production Worker\n", 1
    )[0]
    assert "production_url=https://ai.szolotov.com" in smoke
    assert 'urls=("$production_url")' in smoke
    assert 'scripts/smoke_site.sh "$target" "$TAG" greenblacked-ai' in smoke


def test_production_deploys_are_serialized_across_release_tags():
    workflow = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "  group: release-${{ github.ref }}" in workflow
    cloudflare = workflow.split("  cloudflare:\n", 1)[1]
    job_header = cloudflare.split("    steps:\n", 1)[0]
    assert "    needs: release\n" in job_header
    assert (
        "    concurrency:\n      group: production-cloudflare\n      cancel-in-progress: false\n"
    ) in job_header
    assert job_header.count("      group:") == 1


def test_the_smoke_script_rejects_a_url_that_is_not_https():
    script = REPO / "scripts" / "smoke_site.sh"
    refused = subprocess.run(  # noqa: S603 - the script under test, fixed argv
        [str(script), "http://example.com", "v1", "greenblacked-ai"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 1
    usage = subprocess.run(  # noqa: S603 - the script under test, no arguments
        [str(script)], capture_output=True, text=True, check=False
    )
    assert usage.returncode == 2


class _Versions(http.server.BaseHTTPRequestHandler):
    """Serves version.txt from a script of answers, then the rest of a good catalogue."""

    def do_GET(self):  # noqa: N802 - the http.server hook name
        server = self.server
        if self.path == "/version.txt":
            server.hits += 1
            index = min(server.hits - 1, len(server.answers) - 1)
            body = (server.answers[index] + "\n").encode()
        elif self.path == "/marketplace.json":
            body = b'{"name": "greenblacked-ai"}'
        elif self.path == "/portable-skills.zip":
            body = b"PK\x03\x04"
        else:
            body = b"<html></html>"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _smoke_against(answers, version):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Versions)
    server.answers = answers
    server.hits = 0
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = {**os.environ, "SMOKE_SITE_TEST_MODE": "1"}
        result = subprocess.run(  # noqa: S603 - the script under test, fixed argv
            [
                str(REPO / "scripts" / "smoke_site.sh"),
                f"http://127.0.0.1:{server.server_address[1]}",
                version,
                "greenblacked-ai",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=120,
        )
    finally:
        server.shutdown()
        server.server_close()
    return result, server.hits


def test_the_smoke_script_waits_out_a_host_serving_the_previous_version():
    result, hits = _smoke_against(["v1", "v1", "v1", "v2"], "v2")
    assert result.returncode == 0, result.stderr
    assert hits == 4


def test_the_smoke_script_fails_when_the_version_never_arrives():
    result, hits = _smoke_against(["v1"], "v2")
    assert result.returncode == 1
    assert "version.txt is 'v1' after 3s (" in result.stderr
    assert "expected 'v2'" in result.stderr
    assert hits >= 2


class _Stalls(http.server.BaseHTTPRequestHandler):
    """Accepts every request and answers nothing until long after the wait is over."""

    def do_GET(self):  # noqa: N802 - the http.server hook name
        time.sleep(30)

    def log_message(self, *args):
        pass


def test_the_smoke_wait_is_bounded_by_time_when_a_host_stalls():
    # A stalled host used to cost every attempt its full request timeout; the wait
    # now ends at its time budget, whatever the host does.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Stalls)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    started = time.monotonic()
    try:
        result = subprocess.run(  # noqa: S603 - the script under test, fixed argv
            [
                str(REPO / "scripts" / "smoke_site.sh"),
                f"http://127.0.0.1:{server.server_address[1]}",
                "v2",
                "greenblacked-ai",
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "SMOKE_SITE_TEST_MODE": "1"},
            timeout=60,
        )
    finally:
        server.shutdown()
        server.server_close()
    assert result.returncode == 1
    assert "did not answer" in result.stderr
    assert time.monotonic() - started < 15


def test_the_loopback_hook_accepts_only_a_bare_port():
    script = REPO / "scripts" / "smoke_site.sh"
    for url in ("http://127.0.0.1:1@example.invalid", "http://127.0.0.1:80/x", "http://127.0.0.1:"):
        refused = subprocess.run(  # noqa: S603 - the script under test, fixed argv
            [str(script), url, "v1", "greenblacked-ai"],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "SMOKE_SITE_TEST_MODE": "1"},
            timeout=30,
        )
        assert refused.returncode == 1, url
        assert "must be https" in refused.stderr, url


def test_the_loopback_hook_is_off_by_default():
    script = REPO / "scripts" / "smoke_site.sh"
    env = {k: v for k, v in os.environ.items() if k != "SMOKE_SITE_TEST_MODE"}
    refused = subprocess.run(  # noqa: S603 - the script under test, fixed argv
        [str(script), "http://127.0.0.1:9", "v1", "greenblacked-ai"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert refused.returncode == 1
    assert "must be https" in refused.stderr
    # Even in test mode only the loopback address is accepted over http.
    elsewhere = subprocess.run(  # noqa: S603 - the script under test, fixed argv
        [str(script), "http://example.com", "v1", "greenblacked-ai"],
        capture_output=True,
        text=True,
        check=False,
        env={**env, "SMOKE_SITE_TEST_MODE": "1"},
    )
    assert elsewhere.returncode == 1
    assert "must be https" in elsewhere.stderr
