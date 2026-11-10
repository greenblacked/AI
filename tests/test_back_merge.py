"""`back-merge.yml` and `scripts/back_merge.py`: back-merge pull requests after a promotion.

Two things are pinned here, and both have to hold together.

The workflow must fire only once a promotion pull request has actually merged. Its
trigger and its job `if:` are read out of the real file and checked as text, and the
`if:` is then *evaluated* over a matrix of event payloads — merged and unmerged closes
for both bases, a wrong head branch, a fork head, an opened and a synchronize event — so
the matrix is the workflow's own condition running, not a restatement of it. `act` is not
available on every machine, so the evaluator is a small `ast` walk over the expression
subset the workflow uses, and the script's own `plan()` is asserted to agree with the
workflow on every row, which is what makes the two filters a double check.

The script must open each back-merge once, never push or move a ref, and never touch a
conflict. It talks to GitHub only through an injected `api`, so a fake answers.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess

import pytest

from tests.conftest import REPO, load_script

back_merge = load_script("back_merge.py")

WORKFLOW = REPO / ".github" / "workflows" / "back-merge.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")
REPOSITORY = "greenblacked/AI"


# --- the workflow file --------------------------------------------------------------


def _section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def _job_if() -> str:
    """The job's `if:` folded scalar, joined onto one line."""
    block = _section(TEXT, "    if: >-\n", "    # The `back-merge` environment")
    return " ".join(line.strip() for line in block.splitlines())


def _trigger_types() -> list[str]:
    triggers = _section(TEXT, "\non:\n", "\npermissions:")
    found = re.search(r"^    types: \[([a-z_, ]+)\]$", triggers, re.MULTILINE)
    assert found, triggers
    return [name.strip() for name in found.group(1).split(",")]


def _trigger_branches() -> list[str]:
    triggers = _section(TEXT, "\non:\n", "\npermissions:")
    found = re.search(r"^    branches: \[([a-z_, ]+)\]$", triggers, re.MULTILINE)
    assert found, triggers
    return [name.strip() for name in found.group(1).split(",")]


def test_the_only_trigger_is_a_closed_pull_request_into_stage_or_main():
    triggers = _section(TEXT, "\non:\n", "\npermissions:")
    assert triggers.startswith("  pull_request:\n    types: [closed]\n")
    assert _trigger_types() == ["closed"]
    assert _trigger_branches() == ["stage", "main"]
    # Exactly one event is named: no push, no dispatch, no schedule, and above all not
    # `pull_request_target`, whose privileges nothing here needs.
    events = re.findall(r"^  ([a-z_]+):", triggers, re.MULTILINE)
    assert events == ["pull_request"]
    code = "\n".join(line for line in TEXT.splitlines() if not line.lstrip().startswith("#"))
    for banned in ("pull_request_target", "workflow_dispatch", "workflow_run", "schedule:"):
        assert banned not in code


def test_permissions_are_empty_at_the_top_and_read_plus_pull_requests_on_the_job():
    assert "\npermissions: {}\n" in TEXT
    header = _section(TEXT, "jobs:\n", "    steps:\n")
    permissions = header.split("    permissions:\n", 1)[1].split("    env:\n", 1)[0]
    grants = [line.split("#")[0].strip() for line in permissions.splitlines()]
    assert sorted(grant for grant in grants if grant) == [
        "contents: read",
        "pull-requests: write",
    ]
    assert "contents: write" not in TEXT
    assert "    timeout-minutes: 10\n" in header


def test_the_job_has_one_guarded_job_and_a_literal_concurrency_group():
    assert TEXT.count("\n  back-merge:\n") == 1
    assert (
        "concurrency:\n  group: back-merge-${{ github.event.pull_request.base.ref }}\n"
        "  cancel-in-progress: false\n"
    ) in TEXT


def test_the_app_token_asks_for_two_grants_and_nothing_else():
    step = _section(TEXT, "      - name: Mint an App token", "      - name: Open or refresh")
    assert "if: ${{ env.APP_CONFIGURED == 'true' }}" in step
    assert re.search(r"actions/create-github-app-token@[0-9a-f]{40}  # v\d+\.\d+\.\d+", step)
    permissions = re.findall(r"^          (permission-[a-z-]+): (\w+)$", step, re.MULTILINE)
    assert permissions == [("permission-contents", "read"), ("permission-pull-requests", "write")]
    assert "secrets.BACK_MERGE_APP_CLIENT_ID" in step
    assert "secrets.BACK_MERGE_APP_PRIVATE_KEY" in step
    assert "pat" not in step.lower().replace("path", "")


def test_only_pinned_actions_are_used_and_the_checkout_keeps_no_credential():
    uses = re.findall(r"^\s+- uses: (\S+)", TEXT, re.MULTILINE)
    uses += re.findall(r"^\s+uses: (\S+)", TEXT, re.MULTILINE)
    names = sorted(use.split("@")[0] for use in uses)
    assert names == [
        "actions/checkout",
        "actions/create-github-app-token",
        "actions/setup-python",
    ]
    assert all(re.fullmatch(r".+@[0-9a-f]{40}", use) for use in uses)
    assert "persist-credentials: false" in TEXT
    assert TEXT.count("actions/checkout@") == 1


def test_no_event_value_reaches_a_run_block():
    runs = re.findall(r"^        run: \|\n((?:          .*\n)+)", TEXT, re.MULTILINE)
    assert runs
    for block in runs:
        assert "${{" not in block
        assert "set -Eeuo pipefail" in block
    # The only event-derived values in the file are the concurrency group, the `if:` and
    # nothing in `env:`, `with:` or a command.
    expressions = re.findall(r"\$\{\{[^}]*github\.event[^}]*\}\}", TEXT)
    assert expressions == ["${{ github.event.pull_request.base.ref }}"]


# --- the job `if:`, evaluated ---------------------------------------------------------


def _lookup(path: str, context: dict):
    value = context
    for part in path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def evaluate(expression: str, context: dict):
    """Evaluate the GitHub expression subset the workflow's `if:` uses: `&&`, `||`,
    `==`, string and boolean literals, `startsWith`, and dotted context lookups."""
    source = expression.replace("&&", " and ").replace("||", " or ")
    source = re.sub(r"\btrue\b", "True", source)
    source = re.sub(r"\bfalse\b", "False", source)
    source = re.sub(r"\bgithub\.[A-Za-z_.]+", lambda m: f"_ctx({m.group(0)!r})", source)
    tree = ast.parse(source, mode="eval")

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BoolOp):
            values = (walk(v) for v in node.values)
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare):
            assert len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)
            return walk(node.left) == walk(node.comparators[0])
        if isinstance(node, ast.Call):
            assert isinstance(node.func, ast.Name)
            if node.func.id == "_ctx":
                return _lookup(walk(node.args[0]), context)
            assert node.func.id == "startsWith", node.func.id
            subject, prefix = (walk(arg) for arg in node.args)
            return isinstance(subject, str) and subject.lower().startswith(prefix.lower())
        raise AssertionError(f"unsupported expression node {ast.dump(node)}")

    return walk(tree)


def event(
    action="closed",
    merged=True,
    base="stage",
    head="release/promote-dev-to-stage-0.7.0",
    head_repo=REPOSITORY,
    number=410,
):
    return {
        "action": action,
        "number": number,
        "pull_request": {
            "number": number,
            "merged": merged,
            "base": {"ref": base},
            "head": {"ref": head, "repo": {"full_name": head_repo}},
        },
    }


def fires(payload: dict) -> bool:
    """Whether the workflow would run its job for this event: the trigger first (the
    activity type and the base branch), then the job's `if:`."""
    pull = payload["pull_request"]
    if payload["action"] not in _trigger_types():
        return False
    if pull["base"]["ref"] not in _trigger_branches():
        return False
    context = {"github": {"repository": REPOSITORY, "event": payload}}
    # `github.repository` and `github.event.*` are looked up from this one root.
    return bool(evaluate(_job_if(), context["github"] | {"github": context["github"]}))


# (label, event, whether the workflow runs, back-merges it should open)
MATRIX = [
    ("merged dev-to-stage into stage", event(), True, [("stage", "dev")]),
    (
        "merged stage-to-main into main",
        event(base="main", head="release/promote-stage-to-main-0.7.0"),
        True,
        [("main", "stage"), ("main", "dev")],
    ),
    ("unmerged close into stage", event(merged=False), False, []),
    (
        "unmerged close into main",
        event(merged=False, base="main", head="release/promote-stage-to-main-0.7.0"),
        False,
        [],
    ),
    ("merged, wrong head into stage", event(head="feat/something-else"), False, []),
    (
        "merged, wrong head into main",
        event(base="main", head="feat/something-else"),
        False,
        [],
    ),
    (
        "merged stage-to-main head into stage",
        event(base="stage", head="release/promote-stage-to-main-0.7.0"),
        False,
        [],
    ),
    (
        "merged dev-to-stage head into main",
        event(base="main", head="release/promote-dev-to-stage-0.7.0"),
        False,
        [],
    ),
    ("merged from a fork", event(head_repo="someone/AI"), False, []),
    ("merged into dev", event(base="dev", head="release/promote-dev-to-stage-0.7.0"), False, []),
    ("opened", event(action="opened", merged=False), False, []),
    ("synchronize", event(action="synchronize", merged=False), False, []),
    ("reopened", event(action="reopened", merged=False), False, []),
    ("edited after merge", event(action="edited"), False, []),
    ("opened, already merged flag", event(action="opened"), False, []),
]


@pytest.mark.parametrize(
    ("label", "payload", "runs", "targets"), MATRIX, ids=[m[0] for m in MATRIX]
)
def test_the_workflow_fires_only_on_a_merged_promotion(label, payload, runs, targets):
    assert fires(payload) is runs, label
    # The script's own filter agrees with the workflow's on every row, which is what
    # makes them a double check rather than one check written twice.
    assert back_merge.plan(payload, REPOSITORY) == targets, label


def test_the_matrix_covers_every_case_a_guard_has_to_refuse():
    assert sum(1 for row in MATRIX if row[2]) == 2
    assert len(MATRIX) >= 14


def test_plan_refuses_a_payload_that_is_not_a_pull_request_event():
    assert back_merge.plan({}, REPOSITORY) == []
    assert back_merge.plan({"action": "closed"}, REPOSITORY) == []
    assert back_merge.plan({"action": "closed", "pull_request": "x"}, REPOSITORY) == []
    odd = event()
    odd["pull_request"]["head"]["ref"] = None
    assert back_merge.plan(odd, REPOSITORY) == []
    # `merged` must be exactly true, not merely truthy.
    truthy = event()
    truthy["pull_request"]["merged"] = "true"
    assert back_merge.plan(truthy, REPOSITORY) == []


# --- the script, against a fake API ---------------------------------------------------


class FakeGitHub:
    """Answers the handful of endpoints `back_merge` calls, and records every call."""

    def __init__(self, *, open_pulls=None, ahead=3, mergeable=(True,), create_error=None):
        self.calls: list[tuple[str, str, object]] = []
        self.open_pulls = open_pulls or {}
        self.ahead = ahead
        self.mergeable = list(mergeable)
        self.create_error = create_error
        self.created: list[dict] = []

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and "/pulls?" in path:
            found = re.search(r"base=([^&]+)&head=[^:]+:([^&]+)", path)
            key = (found.group(2), found.group(1))
            return [{"number": self.open_pulls[key]}] if key in self.open_pulls else []
        if method == "GET" and "/compare/" in path:
            return {"ahead_by": self.ahead}
        if method == "POST" and path.endswith("/pulls"):
            if self.create_error:
                raise self.create_error
            self.created.append(body)
            return {"number": 500 + len(self.created)}
        if method == "GET" and re.search(r"/pulls/\d+$", path):
            answer = self.mergeable.pop(0) if len(self.mergeable) > 1 else self.mergeable[0]
            return {"mergeable": answer}
        if method == "PATCH" and re.search(r"/pulls/\d+$", path):
            return {}
        raise AssertionError(f"unexpected call {method} {path}")

    def methods(self):
        return [(method, path.split("?")[0]) for method, path, _ in self.calls]


def run(api, source="stage", destination="dev", number=410, *, app_token=True):
    return back_merge.back_merge(
        api, REPOSITORY, source, destination, number, app_token=app_token, sleep=lambda _: None
    )


def test_a_back_merge_is_opened_from_the_source_branch_itself(capsys):
    api = FakeGitHub()
    result = run(api)
    assert result == {
        "back_merge": "stage into dev",
        "pull_request": "#501",
        "result": "opened",
    }
    (created,) = api.created
    assert created["head"] == "stage" and created["base"] == "dev"
    assert created["title"] == "Merge stage into dev after the promotion in #410"
    assert back_merge.MARKER in created["body"]
    assert "merge commit, not squashed" in created["body"]
    assert "Conflicts" not in created["body"].split("**Conflicts:**", 1)[1].split("\n", 1)[1]
    # Nothing writes to a ref or a branch: the only write is the pull request itself.
    writes = [(m, p) for m, p in api.methods() if m != "GET"]
    assert writes == [("POST", f"repos/{REPOSITORY}/pulls")]
    assert not [p for _, p in api.methods() if "/git/" in p]


def test_a_second_run_with_the_pull_request_open_does_nothing(capsys):
    api = FakeGitHub(open_pulls={("stage", "dev"): 77})
    result = run(api)
    assert result["result"] == "already open" and result["pull_request"] == "#77"
    assert [m for m, _ in api.methods() if m != "GET"] == []
    assert "already merges stage into dev" in capsys.readouterr().out


def test_a_pair_with_nothing_to_merge_is_skipped_cleanly(capsys):
    api = FakeGitHub(ahead=0)
    assert run(api)["result"] == "nothing to merge"
    assert [m for m, _ in api.methods() if m != "GET"] == []
    assert "nothing to merge" in capsys.readouterr().out


def test_a_conflict_is_flagged_with_manual_steps_and_never_resolved(capsys):
    api = FakeGitHub(mergeable=(False,))
    result = run(api, "main", "stage", 411)
    assert result["result"] == "opened, conflicts"
    patch = next(body for method, _, body in api.calls if method == "PATCH")
    assert set(patch) == {"body"}
    assert "## Conflicts" in patch["body"]
    assert "git merge origin/stage" in patch["body"]
    assert "chore/back-merge-main-into-stage" in patch["body"]
    assert "::warning::" in capsys.readouterr().out
    assert not [p for _, p in api.methods() if "/git/" in p]


def test_a_clean_pull_request_is_not_patched():
    api = FakeGitHub(mergeable=(True,))
    run(api)
    assert not [m for m, _, _ in api.calls if m == "PATCH"]


def test_mergeability_is_polled_until_github_answers():
    api = FakeGitHub(mergeable=(None, None, True))
    run(api)
    polls = [c for c in api.calls if c[0] == "GET" and re.search(r"/pulls/\d+$", c[1])]
    assert len(polls) == 3


def test_a_mergeability_that_never_arrives_is_not_called_a_conflict():
    api = FakeGitHub(mergeable=(None,))
    assert run(api)["result"] == "opened"
    polls = [c for c in api.calls if c[0] == "GET" and re.search(r"/pulls/\d+$", c[1])]
    assert len(polls) == back_merge.MERGEABLE_POLLS
    assert not [m for m, _, _ in api.calls if m == "PATCH"]


def test_without_the_app_token_the_pull_request_says_its_checks_did_not_start(capsys):
    api = FakeGitHub()
    run(api, app_token=False)
    body = api.created[0]["body"]
    assert "Close and reopen it" in body
    assert "::warning::#501 was opened with the workflow token" in capsys.readouterr().out
    with_app = FakeGitHub()
    run(with_app, app_token=True)
    assert "Close and reopen it" not in with_app.created[0]["body"]


def test_a_refused_creation_is_annotated_and_raised(capsys):
    error = back_merge.ApiError(403, "GitHub Actions is not permitted to create pull requests")
    api = FakeGitHub(create_error=error)
    with pytest.raises(back_merge.ApiError):
        run(api)
    out = capsys.readouterr().out
    assert "::error::could not open stage into dev" in out
    assert "Settings > Actions > General" in out


def _write_event(tmp_path, payload):
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_main_opens_both_back_merges_after_a_main_promotion(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GH_REPO", REPOSITORY)
    monkeypatch.setenv(
        "GITHUB_EVENT_PATH",
        str(_write_event(tmp_path, event(base="main", head="release/promote-stage-to-main-0.7.0"))),
    )
    monkeypatch.setenv("BACK_MERGE_TOKEN", "app")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    api = FakeGitHub()
    assert back_merge.main([], api) == 0
    assert [(c["head"], c["base"]) for c in api.created] == [("main", "stage"), ("main", "dev")]
    text = summary.read_text(encoding="utf-8")
    assert "| main into stage | #501 | opened |" in text
    assert "| main into dev | #502 | opened |" in text


def test_main_does_nothing_for_an_event_that_is_not_a_merged_promotion(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("GH_REPO", REPOSITORY)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(_write_event(tmp_path, event(merged=False))))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    api = FakeGitHub()
    assert back_merge.main([], api) == 0
    assert api.calls == []
    assert "nothing to do" in capsys.readouterr().out


def test_main_keeps_going_after_one_back_merge_fails_and_then_fails_the_job(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("GH_REPO", REPOSITORY)
    monkeypatch.setenv(
        "GITHUB_EVENT_PATH",
        str(_write_event(tmp_path, event(base="main", head="release/promote-stage-to-main-0.7.0"))),
    )
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.delenv("BACK_MERGE_TOKEN", raising=False)
    failing = FakeGitHub(create_error=back_merge.ApiError(500, "boom"))
    assert back_merge.main([], failing) == 1
    # Both targets were tried: the first failure did not stop the second.
    assert sum(1 for m, p, _ in failing.calls if m == "POST") == 2


# --- gh_api and annotations -----------------------------------------------------------


class Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def test_gh_api_sends_json_on_stdin_and_parses_the_answer(monkeypatch):
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"], seen["input"] = command, kwargs["input"]
        return Completed(stdout='{"number": 9}')

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert back_merge.gh_api("POST", "repos/o/r/pulls", {"title": "x"}) == {"number": 9}
    assert seen["command"] == ["gh", "api", "--method", "POST", "repos/o/r/pulls", "--input", "-"]
    assert json.loads(seen["input"]) == {"title": "x"}


def test_gh_api_reads_without_a_body_and_tolerates_an_empty_answer(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda c, **k: Completed(stdout=""))
    assert back_merge.gh_api("GET", "repos/o/r/pulls") is None


def test_gh_api_raises_with_the_status_it_can_read(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda c, **k: Completed(1, stderr="gh: Not Found (HTTP 404)")
    )
    with pytest.raises(back_merge.ApiError) as raised:
        back_merge.gh_api("GET", "repos/o/r/pulls/1")
    assert raised.value.status == 404
    monkeypatch.setattr(subprocess, "run", lambda c, **k: Completed(1, stdout="no network"))
    with pytest.raises(back_merge.ApiError) as raised:
        back_merge.gh_api("GET", "repos/o/r/pulls/1")
    assert raised.value.status is None


def test_an_annotation_cannot_start_a_second_workflow_command(capsys):
    back_merge.annotate("warning", "line one\n::error::injected 100%")
    assert capsys.readouterr().out == "::warning::line one%0A::error::injected 100%25\n"


def test_the_summary_is_skipped_without_a_summary_file(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    back_merge.write_summary([{"back_merge": "a into b", "result": "x"}])
