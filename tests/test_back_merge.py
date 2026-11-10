"""`back-merge.yml` and `scripts/back_merge.py`: back-merge pull requests after a promotion.

Two things are pinned here, and both have to hold together.

The workflow must act only once a promotion pull request has actually merged. It runs on
a `push` to `stage` or `main`, so two filters stand between a push and a back-merge: the
workflow's trigger and job `if:`, which decide whether the job runs at all, and the
script, which asks GitHub which pull request the pushed commit belongs to and acts only
on a merged promotion whose `merge_commit_sha` is that commit. Both are read out of the
real files. The `if:` is *evaluated*, by a small `ast` walk over the expression subset the
workflow uses (`act` is not available on every machine), and the script runs against a
fake API, over one matrix of events: merged and unmerged promotions for both bases, a
direct push, a `merge_commit_sha` that is not the pushed commit, a wrong base, a fork, a
wrong or look-alike head prefix, and pushes and events that must not run the job.

The script must open each back-merge once, from a branch it creates and never moves,
never touch a conflict, and never act without the App's token. It talks to GitHub only through an
injected `api`, so a fake answers.
"""

from __future__ import annotations

import ast
import fnmatch
import json
import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import REPO, load_script

back_merge = load_script("back_merge.py")

WORKFLOW = REPO / ".github" / "workflows" / "back-merge.yml"
TEXT = WORKFLOW.read_text(encoding="utf-8")
REPOSITORY = "greenblacked/AI"


# --- the workflow file --------------------------------------------------------------


def _section(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def _code() -> str:
    """The workflow without its comment lines."""
    return "\n".join(line for line in TEXT.splitlines() if not line.lstrip().startswith("#"))


def _job_if() -> str:
    """The job's `if:` folded scalar, joined onto one line."""
    block = _section(TEXT, "    if: >-\n", "    # The `back-merge` environment")
    return " ".join(line.strip() for line in block.splitlines())


def _trigger_events() -> list[str]:
    triggers = _section(TEXT, "\non:\n", "\npermissions:")
    return re.findall(r"^  ([a-z_]+):", triggers, re.MULTILINE)


def _trigger_branches() -> list[str]:
    triggers = _section(TEXT, "\non:\n", "\npermissions:")
    found = re.search(r"^    branches: \[([a-z_, ]+)\]$", triggers, re.MULTILINE)
    assert found, triggers
    return [name.strip() for name in found.group(1).split(",")]


def test_the_only_trigger_is_a_push_to_stage_or_main():
    triggers = _section(TEXT, "\non:\n", "\npermissions:")
    assert triggers == "  push:\n    branches: [stage, main]\n"
    assert _trigger_events() == ["push"]
    assert _trigger_branches() == ["stage", "main"]
    # No pull request event of any kind, no tag, no dispatch, no schedule: a push to a
    # protected branch is what a merged pull request is, and nothing else here starts it.
    for banned in (
        "pull_request",
        "pull_request_target",
        "workflow_dispatch",
        "workflow_run",
        "schedule:",
        "tags:",
        "paths:",
    ):
        assert banned not in _code()


def test_a_push_to_a_back_merge_branch_cannot_start_the_workflow():
    # The trigger is exactly these two literal branches: a branch the job itself creates
    # can never match, so the workflow cannot start itself.
    assert _trigger_branches() == ["stage", "main"]
    created = "chore/back-merge-stage-to-dev-abc1234"
    for pattern in _trigger_branches():
        assert not fnmatch.fnmatchcase(created, pattern)
        assert "*" not in pattern and "?" not in pattern
    assert not job_runs("push", f"refs/heads/{created}")
    assert not evaluate(
        _job_if(), {"github": {"event_name": "push", "ref": f"refs/heads/{created}"}}
    )


def test_the_workflow_makes_no_commit_push_merge_or_deletion():
    code = _code()
    for banned in ("git push", "git commit", "git merge", "git branch -d", "--delete", "DELETE"):
        assert banned not in code
    assert "git " not in code.replace("github", "").replace("git/", "")


def test_permissions_are_empty_at_the_top_and_read_only_on_the_job():
    assert "\npermissions: {}\n" in TEXT
    header = _section(TEXT, "jobs:\n", "    steps:\n")
    permissions = header.split("    permissions:\n", 1)[1].split("    env:\n", 1)[0]
    grants = [line.split("#")[0].strip() for line in permissions.splitlines()]
    # The workflow token only checks out: every write is done with the App's token.
    assert [grant for grant in grants if grant] == ["contents: read"]
    assert "contents: write\n    env:" not in TEXT
    assert "pull-requests: write\n    env:" not in TEXT
    assert "    timeout-minutes: 10\n" in header


def test_the_job_runs_in_the_back_merge_environment_with_a_literal_concurrency_group():
    assert TEXT.count("\n  back-merge:\n") == 1
    assert "    environment: back-merge\n" in TEXT
    assert (
        "concurrency:\n  group: back-merge-${{ github.ref_name }}\n  cancel-in-progress: false\n"
    ) in TEXT


def test_the_app_token_asks_for_contents_and_pull_requests_write_and_nothing_else():
    step = _section(TEXT, "      - name: Mint an App token", "      - name: Open the back-merge")
    assert "if: ${{ env.APP_CONFIGURED == 'true' }}" in step
    assert re.search(r"actions/create-github-app-token@[0-9a-f]{40}  # v\d+\.\d+\.\d+", step)
    permissions = re.findall(r"^          (permission-[a-z-]+): (\w+)$", step, re.MULTILINE)
    assert permissions == [("permission-contents", "write"), ("permission-pull-requests", "write")]
    assert "secrets.BACK_MERGE_APP_CLIENT_ID" in step
    assert "secrets.BACK_MERGE_APP_PRIVATE_KEY" in step


def test_there_is_no_fallback_to_the_workflow_token():
    code = _code()
    assert "GITHUB_TOKEN" not in code
    assert "github.token" not in code
    final = _section(TEXT, "      - name: Open the back-merge", "\n  zzz")
    assert "GH_TOKEN: ${{ steps.app.outputs.token }}" in final
    assert "BACK_MERGE_TOKEN: app\n" in final


def test_without_the_app_the_job_only_says_so():
    steps = TEXT.split("    steps:\n", 1)[1].split("\n      - ")
    gates = {step.split("\n", 1)[0]: step for step in steps}
    unconfigured = [step for step in steps if "env.APP_CONFIGURED != 'true'" in step]
    configured = [step for step in steps if "env.APP_CONFIGURED == 'true'" in step]
    assert len(unconfigured) == 1 and len(configured) == 4 and len(gates) == 5
    notice = unconfigured[0]
    assert "::notice title=back-merge::" in notice
    assert "BACK_MERGE_APP_CLIENT_ID" in notice and "BACK_MERGE_APP_PRIVATE_KEY" in notice
    # The notice step runs nothing from the repository and calls no API.
    assert "python" not in notice and "gh " not in notice


def test_only_pinned_actions_are_used_and_the_checkout_keeps_no_credential():
    uses = re.findall(r"^\s+(?:- )?uses: (\S+)", TEXT, re.MULTILINE)
    names = sorted(use.split("@")[0] for use in uses)
    assert names == [
        "actions/checkout",
        "actions/create-github-app-token",
        "actions/setup-python",
    ]
    assert all(re.fullmatch(r".+@[0-9a-f]{40}", use) for use in uses)
    assert "persist-credentials: false" in TEXT
    assert TEXT.count("actions/checkout@") == 1
    # No `ref:`: on a push the checkout is the protected branch's tip, not a merge ref.
    checkout = _section(
        TEXT, "      - uses: actions/checkout", "      - uses: actions/setup-python"
    )
    assert "ref:" not in "\n".join(
        line for line in checkout.splitlines() if not line.lstrip().startswith("#")
    )


def test_no_event_value_reaches_a_run_block():
    runs = re.findall(r"^        run: \|\n((?:          .*\n)+)", TEXT, re.MULTILINE)
    assert len(runs) == 2
    for block in runs:
        assert "${{" not in block
        assert "set -Eeuo pipefail" in block
    # The only event-derived expression in the file is the concurrency group's branch.
    assert re.findall(r"\$\{\{[^}]*github\.event[^}]*\}\}", TEXT) == []
    assert re.findall(r"\$\{\{ github\.ref_name \}\}", TEXT) == ["${{ github.ref_name }}"]


# --- the job `if:`, evaluated ---------------------------------------------------------


def evaluate(expression: str, context: dict):
    """Evaluate the GitHub expression subset the workflow's `if:` uses: `&&`, `||`,
    `==`, string and boolean literals, `startsWith`, and dotted context lookups."""
    source = expression.replace("&&", " and ").replace("||", " or ")
    source = re.sub(r"\btrue\b", "True", source)
    source = re.sub(r"\bfalse\b", "False", source)
    source = re.sub(r"\bgithub\.[A-Za-z_.]+", lambda m: f"_ctx({m.group(0)!r})", source)
    tree = ast.parse(source, mode="eval")

    def lookup(path: str):
        value = context
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return value

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
                return lookup(walk(node.args[0]))
            assert node.func.id == "startsWith", node.func.id
            subject, prefix = (walk(arg) for arg in node.args)
            return isinstance(subject, str) and subject.lower().startswith(prefix.lower())
        raise AssertionError(f"unsupported expression node {ast.dump(node)}")

    return walk(tree)


def job_runs(event_name: str, ref: str) -> bool:
    """Whether the workflow runs its job for this event: the trigger's event and branch
    filter first, then the job's `if:`."""
    if event_name not in _trigger_events():
        return False
    if ref.removeprefix("refs/heads/") not in _trigger_branches() or "refs/heads/" not in ref:
        return False
    return bool(evaluate(_job_if(), {"github": {"event_name": event_name, "ref": ref}}))


SHA = "a" * 40
OTHER = "b" * 40
STAGE_HEAD = "release/promote-dev-to-stage-0.7.0"
MAIN_HEAD = "release/promote-stage-to-main-0.7.0"


def pull(
    number=410,
    *,
    merged=True,
    base="stage",
    head=STAGE_HEAD,
    head_repo=REPOSITORY,
    merge_sha=SHA,
    state="closed",
):
    return {
        "number": number,
        "state": state,
        "merged": merged,
        "merge_commit_sha": merge_sha,
        "base": {"ref": base},
        "head": {"ref": head, "repo": {"full_name": head_repo}},
    }


def push(ref="refs/heads/stage", after=SHA):
    return {"ref": ref, "after": after, "repository": {"full_name": REPOSITORY}}


MAIN_TARGETS = [("main", "stage"), ("main", "dev")]

# (label, event name, pushed event, the pull requests GitHub lists for the pushed commit,
#  whether the workflow runs its job, the back-merges the script opens)
MATRIX = [
    ("merged dev-to-stage into stage", "push", push(), [pull()], True, [("stage", "dev")]),
    (
        "merged stage-to-main into main",
        "push",
        push("refs/heads/main"),
        [pull(base="main", head=MAIN_HEAD)],
        True,
        MAIN_TARGETS,
    ),
    ("direct push, no pull request", "push", push(), [], True, []),
    (
        "direct push to main, no pull request",
        "push",
        push("refs/heads/main"),
        [],
        True,
        [],
    ),
    (
        "squash or rebase: merge_commit_sha is not the pushed commit, stage",
        "push",
        push(),
        [pull(merge_sha=OTHER)],
        True,
        [],
    ),
    (
        "squash or rebase: merge_commit_sha is not the pushed commit, main",
        "push",
        push("refs/heads/main"),
        [pull(base="main", head=MAIN_HEAD, merge_sha=OTHER)],
        True,
        [],
    ),
    (
        "promotion into main listed for a push to stage (wrong base)",
        "push",
        push(),
        [pull(base="main", head=MAIN_HEAD)],
        True,
        [],
    ),
    ("merged from a fork", "push", push(), [pull(head_repo="someone/AI")], True, []),
    ("wrong head prefix", "push", push(), [pull(head="feat/something-else")], True, []),
    (
        "look-alike head prefix, no separator",
        "push",
        push(),
        [pull(head="release/promote-dev-to-stagex")],
        True,
        [],
    ),
    (
        "dev-to-stage head, but merged into main, listed for a push to stage",
        "push",
        push(),
        [pull(base="main", head=STAGE_HEAD)],
        True,
        [],
    ),
    (
        "stage-to-main head merged into stage",
        "push",
        push(),
        [pull(head=MAIN_HEAD)],
        True,
        [],
    ),
    (
        "dev-to-stage head merged into main",
        "push",
        push("refs/heads/main"),
        [pull(base="main", head=STAGE_HEAD)],
        True,
        [],
    ),
    (
        "unmerged pull request that carries the pushed commit",
        "push",
        push(),
        [pull(merged=False, state="open")],
        True,
        [],
    ),
    (
        "closed unmerged, merge_commit_sha equal to the pushed commit",
        "push",
        push(),
        [pull(merged=False)],
        True,
        [],
    ),
    (
        "the merge of a back-merge pull request itself (head is main)",
        "push",
        push(),
        [pull(base="stage", head="main")],
        True,
        [],
    ),
    (
        "head named exactly the prefix",
        "push",
        push(),
        [pull(head="release/promote-dev-to-stage")],
        True,
        [("stage", "dev")],
    ),
    (
        "head with a slash after the prefix",
        "push",
        push(),
        [pull(head="release/promote-dev-to-stage/0.7.0")],
        True,
        [("stage", "dev")],
    ),
    (
        "several pull requests on the commit, one is the promotion",
        "push",
        push(),
        [pull(1, head="feat/other"), pull(2, merge_sha=OTHER), pull(3)],
        True,
        [("stage", "dev")],
    ),
    ("push to dev", "push", push("refs/heads/dev"), [pull()], False, []),
    (
        "push of a back-merge branch (no loop)",
        "push",
        push("refs/heads/chore/back-merge-stage-to-dev-aaaaaaa"),
        [pull(base="dev", head=STAGE_HEAD)],
        False,
        [],
    ),
    ("push to a topic branch", "push", push("refs/heads/ci/x"), [pull()], False, []),
    ("tag push", "push", push("refs/tags/v0.7.0"), [pull()], False, []),
    ("pull request opened", "pull_request", push(), [pull()], False, []),
    ("pull request closed and merged", "pull_request", push(), [pull()], False, []),
    ("pull request synchronize", "pull_request", push(), [pull()], False, []),
    ("manual dispatch", "workflow_dispatch", push(), [pull()], False, []),
    ("branch deleted", "push", push(after="0" * 40), [pull()], True, []),
]


class FakeGitHub:
    """Answers the handful of endpoints `back_merge` calls, and records every call."""

    def __init__(
        self,
        *,
        listed=(),
        open_heads=(),
        refs=None,
        ahead=3,
        mergeable=(True,),
        create_error=None,
        ref_error=None,
        race=False,
    ):
        self.calls: list[tuple[str, str, object]] = []
        self.listed = list(listed)
        # (head ref, base, head repo) of pull requests that are open
        self.open_heads = list(open_heads)
        self.refs = dict(refs or {})  # chore branches that exist, name -> sha
        self.ahead = ahead
        self.mergeable = list(mergeable)
        self.create_error = create_error
        self.ref_error = ref_error
        self.race = race
        self.created: list[dict] = []
        self.next_number = 500

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and re.search(r"/commits/[0-9a-f]{40}/pulls\?", path):
            return [{"number": item["number"]} for item in self.listed]
        if method == "GET" and re.search(r"/pulls/\d+$", path):
            number = int(path.rsplit("/", 1)[1])
            for item in self.listed:
                if item["number"] == number:
                    return item
            value = self.mergeable.pop(0) if len(self.mergeable) > 1 else self.mergeable[0]
            return {"mergeable": value}
        if method == "GET" and "/pulls?" in path:
            base = re.search(r"base=([^&]+)", path).group(1)
            page = int(re.search(r"[&?]page=(\d+)", path).group(1))
            matching = [
                {"number": 900 + i, "head": {"ref": ref, "repo": {"full_name": repo}}}
                for i, (ref, b, repo) in enumerate(self.open_heads)
                if b == base
            ]
            return matching[(page - 1) * 100 : page * 100]
        if method == "GET" and "/git/ref/heads/" in path:
            name = path.split("/git/ref/heads/", 1)[1]
            if self.ref_error and name.startswith("chore/"):
                raise self.ref_error
            if name in ("stage", "main", "dev"):
                return {"object": {"sha": SHA}}
            if name in self.refs:
                return {"object": {"sha": self.refs[name]}}
            raise back_merge.ApiError(404, "Not Found (HTTP 404)")
        if method == "POST" and path.endswith("/git/refs"):
            if self.race:
                self.refs[body["ref"].removeprefix("refs/heads/")] = body["sha"]
                raise back_merge.ApiError(422, "Reference already exists (HTTP 422)")
            if self.create_error:
                raise self.create_error
            self.refs[body["ref"].removeprefix("refs/heads/")] = body["sha"]
            return {}
        if method == "GET" and "/compare/" in path:
            return {"ahead_by": self.ahead}
        if method == "POST" and path.endswith("/pulls"):
            self.created.append(body)
            self.next_number += 1
            return {"number": self.next_number}
        if method == "PATCH" and re.search(r"/pulls/\d+$", path):
            return {}
        raise AssertionError(f"unexpected call {method} {path}")

    def methods(self):
        return [(method, path.split("?")[0]) for method, path, _ in self.calls]

    def writes(self):
        return [(m, p) for m, p in self.methods() if m != "GET"]

    def pairs(self):
        """(source, destination) of each pull request opened, read from its head name."""
        found = []
        for body in self.created:
            parsed = re.fullmatch(
                r"chore/back-merge-(stage|main)-to-(dev|stage)-[0-9a-f]{7}", body["head"]
            )
            assert parsed, body["head"]
            assert body["base"] == parsed.group(2)
            found.append((parsed.group(1), parsed.group(2)))
        return found


def _run_main(tmp_path, monkeypatch, payload, api, *, token="app"):  # noqa: S107
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("GH_REPO", REPOSITORY)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    if token is None:
        monkeypatch.delenv("BACK_MERGE_TOKEN", raising=False)
    else:
        monkeypatch.setenv("BACK_MERGE_TOKEN", token)
    return back_merge.main([], api)


@pytest.mark.parametrize(
    ("label", "event_name", "payload", "listed", "runs", "targets"),
    MATRIX,
    ids=[m[0] for m in MATRIX],
)
def test_back_merges_open_only_for_a_merged_promotion_push(
    label, event_name, payload, listed, runs, targets, tmp_path, monkeypatch
):
    # 1. Does the workflow run its job at all?
    assert job_runs(event_name, payload["ref"]) is runs, label
    # 2. When it does, does the script open what the promotion calls for, and only that?
    api = FakeGitHub(listed=listed)
    if runs:
        assert _run_main(tmp_path, monkeypatch, payload, api) == 0
    assert api.pairs() == targets, label
    # Whatever happened, the only writes are a new chore/ branch and a pull request: no
    # ref moved, no force, no merge.
    assert {(m, p) for m, p in api.writes()} <= {
        ("POST", f"repos/{REPOSITORY}/git/refs"),
        ("POST", f"repos/{REPOSITORY}/pulls"),
    }, label
    assert all("force" not in (body or {}) for _, _, body in api.calls), label
    ref_bodies = [b for m, p, b in api.calls if m == "POST" and p.endswith("/git/refs")]
    assert all(
        b["ref"].startswith("refs/heads/chore/back-merge-") and b["sha"] == payload["after"]
        for b in ref_bodies
    ), label
    # PATCH is only ever a pull request body, never a ref.
    assert all("/git/" not in p for m, p, _ in api.calls if m == "PATCH"), label


@pytest.mark.parametrize(
    ("event_name", "ref", "expected"),
    [
        ("push", "refs/heads/stage", True),
        ("push", "refs/heads/main", True),
        ("push", "refs/heads/dev", False),
        ("push", "refs/tags/stage", False),
        ("pull_request", "refs/heads/stage", False),
        ("pull_request", "refs/pull/1/merge", False),
        ("workflow_dispatch", "refs/heads/main", False),
    ],
)
def test_the_job_if_alone_admits_only_a_push_to_the_two_branches(event_name, ref, expected):
    # Independent of the trigger: if the `on:` block were ever widened, the job would
    # still refuse everything but a push to stage or main.
    context = {"github": {"event_name": event_name, "ref": ref}}
    assert bool(evaluate(_job_if(), context)) is expected


def test_the_matrix_covers_what_a_guard_has_to_refuse():
    assert len(MATRIX) >= 25
    assert sum(1 for row in MATRIX if row[5]) == 5  # the rows that open anything
    assert sum(1 for row in MATRIX if not row[4]) == 8  # the rows the job never runs for


@pytest.mark.parametrize(
    ("head", "prefix", "expected"),
    [
        ("release/promote-dev-to-stage", "release/promote-dev-to-stage", True),
        ("release/promote-dev-to-stage-0.6.0-live-ops", "release/promote-dev-to-stage", True),
        ("release/promote-dev-to-stage/x", "release/promote-dev-to-stage", True),
        ("release/promote-dev-to-stagex", "release/promote-dev-to-stage", False),
        ("release/promote-dev-to-stage.1", "release/promote-dev-to-stage", False),
        ("xrelease/promote-dev-to-stage", "release/promote-dev-to-stage", False),
        ("release/promote-dev-to-stag", "release/promote-dev-to-stage", False),
    ],
)
def test_the_head_prefix_is_anchored(head, prefix, expected):
    assert back_merge.head_matches(head, prefix) is expected


def test_plan_requires_every_condition_and_reads_only_the_pull_request():
    assert back_merge.plan(pull(), REPOSITORY, "stage", SHA) == [("stage", "dev")]
    assert back_merge.plan(pull(base="main", head=MAIN_HEAD), REPOSITORY, "main", SHA) == (
        MAIN_TARGETS
    )
    assert back_merge.plan(None, REPOSITORY, "stage", SHA) == []
    assert back_merge.plan("x", REPOSITORY, "stage", SHA) == []
    odd = pull()
    odd["head"]["ref"] = None
    assert back_merge.plan(odd, REPOSITORY, "stage", SHA) == []
    truthy = pull()
    truthy["merged"] = "true"  # exactly true, not merely truthy
    assert back_merge.plan(truthy, REPOSITORY, "stage", SHA) == []
    assert back_merge.plan(pull(), REPOSITORY, "dev", SHA) == []
    assert back_merge.plan(pull(base="dev"), REPOSITORY, "dev", SHA) == []


def test_resolve_skips_candidates_that_are_not_pull_requests():
    api = FakeGitHub(listed=[pull()])

    def with_junk(method, path, body=None):
        if "/commits/" in path:
            return ["x", {"number": "nope"}, {"number": 410}]
        return api(method, path, body)

    assert back_merge.resolve(with_junk, REPOSITORY, "stage", SHA) == (410, [("stage", "dev")])
    assert back_merge.resolve(lambda *a, **k: None, REPOSITORY, "stage", SHA) is None


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"ref": "refs/heads/stage"},
        {"ref": "refs/heads/stage", "after": "abc"},
        {"ref": "refs/heads/stage", "after": "A" * 40},
        {"ref": "refs/heads/stage", "after": "0" * 40},
        {"ref": "refs/heads/dev", "after": SHA},
        {"ref": "stage", "after": SHA},
        {"ref": "refs/tags/stage", "after": SHA},
        {"ref": "refs/heads/stage/x", "after": SHA},
    ],
)
def test_push_target_refuses_anything_but_a_commit_on_stage_or_main(payload):
    assert back_merge.push_target(payload) is None


def test_push_target_names_the_branch_and_commit():
    assert back_merge.push_target(push()) == ("stage", SHA)
    assert back_merge.push_target(push("refs/heads/main")) == ("main", SHA)


# --- the script, against a fake API ---------------------------------------------------


def run(api, source="stage", destination="dev", number=410):
    return back_merge.back_merge(
        api, REPOSITORY, source, destination, number, SHA, sleep=lambda _: None
    )


def test_a_back_merge_is_opened_from_a_new_branch_cut_at_the_pushed_commit():
    api = FakeGitHub()
    result = run(api)
    assert result == {"back_merge": "stage into dev", "pull_request": "#501", "result": "opened"}
    branch = f"chore/back-merge-stage-to-dev-{SHA[:7]}"
    assert api.refs == {branch: SHA}
    (created,) = api.created
    assert created["head"] == branch and created["base"] == "dev"
    assert created["title"] == "Merge stage into dev after the promotion in #410"
    assert back_merge.MARKER in created["body"]
    assert "merge commit, not squashed" in created["body"]
    assert branch in created["body"]
    # One branch created, one pull request opened, nothing moved or forced.
    assert api.writes() == [
        ("POST", f"repos/{REPOSITORY}/git/refs"),
        ("POST", f"repos/{REPOSITORY}/pulls"),
    ]
    ref_call = next(c for c in api.calls if c[0] == "POST" and c[1].endswith("/git/refs"))
    assert ref_call[2] == {"ref": f"refs/heads/{branch}", "sha": SHA}
    assert not [m for m, _ in api.methods() if m in ("PATCH", "PUT", "DELETE")]


def test_the_branch_name_is_a_valid_branch_for_the_naming_check():
    naming = load_script("check_naming.py")
    for source, destination in (("stage", "dev"), ("main", "stage"), ("main", "dev")):
        name = back_merge.branch_for(source, destination, SHA)
        assert naming.branch_problem(name) is None, name


@pytest.mark.parametrize("existing_sha", [SHA, "d" * 40])
def test_an_existing_branch_without_an_open_pull_request_fails_and_is_left_alone(
    existing_sha, capsys
):
    # Whatever commit it points at: never reused, never moved, never forced.
    branch = f"chore/back-merge-stage-to-dev-{SHA[:7]}"
    api = FakeGitHub(refs={branch: existing_sha})
    with pytest.raises(back_merge.BranchExistsError, match="already exists"):
        run(api)
    assert api.refs == {branch: existing_sha}
    assert api.writes() == []
    out = capsys.readouterr().out
    assert "::error::" in out and "was left as it is" in out


def test_an_existing_branch_with_an_open_pull_request_is_skipped_without_touching_it(capsys):
    branch = f"chore/back-merge-stage-to-dev-{SHA[:7]}"
    api = FakeGitHub(refs={branch: SHA}, open_heads=[(branch, "dev", REPOSITORY)])
    result = run(api)
    assert result["result"] == "already open" and result["pull_request"] == "#900"
    assert api.writes() == []
    assert not [c for c in api.calls if "/git/" in c[1]]


def test_a_branch_created_by_a_run_in_between_is_a_failure_not_a_reuse(capsys):
    api = FakeGitHub(race=True)
    with pytest.raises(back_merge.BranchExistsError):
        run(api)
    assert api.created == []
    assert "::error::" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["dev", "stage", "main", "feat/x", "chore/other", "release/x"])
def test_a_ref_outside_the_back_merge_namespace_is_never_created(name):
    api = FakeGitHub()
    with pytest.raises(ValueError, match="refusing"):
        back_merge.ensure_branch(api, REPOSITORY, name, SHA)
    assert api.calls == []


@pytest.mark.parametrize("sha", ["", "abc1234", "A" * 40, "../x", SHA + "a"])
def test_a_ref_is_only_ever_created_at_a_full_lowercase_sha(sha):
    api = FakeGitHub()
    with pytest.raises(ValueError, match="refusing"):
        back_merge.ensure_branch(api, REPOSITORY, "chore/back-merge-stage-to-dev-aaaaaaa", sha)
    assert api.calls == []


def test_the_script_never_deletes_moves_or_forces_a_ref():
    source = Path(back_merge.__file__).read_text(encoding="utf-8")
    assert '"DELETE"' not in source and '"PUT"' not in source
    assert '"force"' not in source and "force=" not in source and "--force" not in source
    patches = re.findall(r'"PATCH",\s*f"([^"]+)"', source)
    assert patches == ["repos/{repo}/pulls/{pull_number}"]
    posts = re.findall(r'"POST",\s*f"([^"]+)"', source)
    assert sorted(posts) == ["repos/{repo}/git/refs", "repos/{repo}/pulls"]


def test_a_failed_ref_lookup_that_is_not_a_404_is_raised():
    api = FakeGitHub(ref_error=back_merge.ApiError(500, "boom (HTTP 500)"))
    with pytest.raises(back_merge.ApiError):
        run(api)
    assert api.writes() == []


def test_a_refused_branch_creation_that_is_not_a_422_is_raised(capsys):
    api = FakeGitHub(create_error=back_merge.ApiError(403, "Resource not accessible"))
    with pytest.raises(back_merge.ApiError) as raised:
        run(api)
    assert raised.value.status == 403
    assert api.created == []
    assert "installed on this repository" in capsys.readouterr().out


def test_a_second_run_with_a_back_merge_open_does_nothing_even_at_another_commit(capsys):
    older = f"chore/back-merge-stage-to-dev-{'e' * 7}"
    api = FakeGitHub(open_heads=[(older, "dev", REPOSITORY)])
    result = run(api)
    assert result["result"] == "already open" and result["pull_request"] == "#900"
    assert api.writes() == []
    assert "already merges stage into dev" in capsys.readouterr().out


@pytest.mark.parametrize(
    "head",
    [
        ("chore/back-merge-stage-to-dev-abc1234", "stage", REPOSITORY),  # another base
        ("chore/back-merge-stage-to-dev-abc1234", "dev", "someone/AI"),  # a fork's branch
        ("chore/back-merge-main-to-dev-abc1234", "dev", REPOSITORY),  # another pair
        ("feat/back-merge-stage-to-dev-abc1234", "dev", REPOSITORY),  # not a back-merge
    ],
)
def test_only_a_back_merge_for_the_same_pair_in_this_repository_counts_as_open(head):
    api = FakeGitHub(open_heads=[head])
    assert run(api)["result"] == "opened"


def test_open_pull_requests_are_read_page_by_page():
    heads = [(f"feat/x-{i}", "dev", REPOSITORY) for i in range(150)]
    heads.append((f"chore/back-merge-stage-to-dev-{'f' * 7}", "dev", REPOSITORY))
    api = FakeGitHub(open_heads=heads)
    assert run(api)["result"] == "already open"
    pages = [p for m, p, _ in api.calls if m == "GET" and "/pulls?" in p]
    assert len(pages) == 2


def test_a_pair_with_nothing_to_merge_is_skipped_cleanly(capsys):
    api = FakeGitHub(ahead=0)
    assert run(api)["result"] == "nothing to merge"
    assert api.writes() == []
    assert "nothing to merge" in capsys.readouterr().out


def test_a_conflict_is_flagged_with_manual_steps_and_never_resolved(capsys):
    api = FakeGitHub(mergeable=(False,))
    result = run(api, "main", "stage", 411)
    assert result["result"] == "opened, conflicts"
    patch = next(body for method, _, body in api.calls if method == "PATCH")
    assert set(patch) == {"body"}
    assert "## Conflicts" in patch["body"]
    assert "git merge origin/stage" in patch["body"]
    assert f"git switch chore/back-merge-main-to-stage-{SHA[:7]}" in patch["body"]
    assert "--force" not in patch["body"]
    assert "::warning::" in capsys.readouterr().out
    assert [p for m, p in api.methods() if m == "PATCH"] == [f"repos/{REPOSITORY}/pulls/501"]


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


def test_a_refused_pull_request_creation_is_annotated_and_raised(capsys):
    class Refusing(FakeGitHub):
        def __call__(self, method, path, body=None):
            if method == "POST" and path.endswith("/pulls"):
                raise back_merge.ApiError(403, "Resource not accessible by integration")
            return super().__call__(method, path, body)

    with pytest.raises(back_merge.ApiError):
        run(Refusing())
    out = capsys.readouterr().out
    assert "::error::could not open chore/back-merge-stage-to-dev-" in out
    assert "installed on this repository" in out
    assert "Settings > Actions" not in out


def test_main_opens_both_back_merges_after_a_main_promotion(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    api = FakeGitHub(listed=[pull(base="main", head=MAIN_HEAD)])
    path = tmp_path / "event.json"
    path.write_text(json.dumps(push("refs/heads/main")), encoding="utf-8")
    monkeypatch.setenv("GH_REPO", REPOSITORY)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
    monkeypatch.setenv("BACK_MERGE_TOKEN", "app")
    assert back_merge.main([], api) == 0
    assert api.pairs() == [("main", "stage"), ("main", "dev")]
    text = summary.read_text(encoding="utf-8")
    assert "| main into stage | #501 | opened |" in text
    assert "| main into dev | #502 | opened |" in text


def test_main_does_nothing_without_the_app_token(tmp_path, monkeypatch, capsys):
    for token in (None, "workflow", ""):
        api = FakeGitHub(listed=[pull()])
        assert _run_main(tmp_path, monkeypatch, push(), api, token=token) == 0
        assert api.calls == []
    assert "no GitHub App token" in capsys.readouterr().out


def test_main_does_nothing_for_a_push_that_is_not_a_promotion(tmp_path, monkeypatch, capsys):
    api = FakeGitHub(listed=[pull(merge_sha=OTHER)])
    assert _run_main(tmp_path, monkeypatch, push(), api) == 0
    assert not api.writes()
    assert "is not the merge of a promotion" in capsys.readouterr().out


def test_main_does_nothing_for_an_event_that_is_not_a_push_to_stage_or_main(
    tmp_path, monkeypatch, capsys
):
    api = FakeGitHub(listed=[pull()])
    assert _run_main(tmp_path, monkeypatch, {"action": "closed", "pull_request": pull()}, api) == 0
    assert api.calls == []
    assert "nothing to do" in capsys.readouterr().out


def test_main_keeps_going_after_one_back_merge_fails_and_then_fails_the_job(tmp_path, monkeypatch):
    failing = FakeGitHub(
        listed=[pull(base="main", head=MAIN_HEAD)],
        create_error=back_merge.ApiError(403, "Resource not accessible"),
    )
    assert _run_main(tmp_path, monkeypatch, push("refs/heads/main"), failing) == 1
    # Both targets were tried: the first failure did not stop the second.
    assert sum(1 for m, p, _ in failing.calls if m == "POST" and p.endswith("/git/refs")) == 2
    assert failing.created == []


def test_the_pushed_commit_goes_into_one_api_path_only_after_it_is_validated(tmp_path, monkeypatch):
    api = FakeGitHub(listed=[pull()])
    _run_main(tmp_path, monkeypatch, push(), api)
    first = api.calls[0]
    assert first[:2] == ("GET", f"repos/{REPOSITORY}/commits/{SHA}/pulls?per_page=100")
    bad = push(after="../../x" + "a" * 33)
    api = FakeGitHub(listed=[pull()])
    assert _run_main(tmp_path, monkeypatch, bad, api) == 0
    assert api.calls == []


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
