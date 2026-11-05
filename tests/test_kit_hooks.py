"""Behaviour tests for the ten kit hooks under `plugins/*/skills/*/assets/hooks/`.

`tests/test_plugin_shape.py` checks what a hook is allowed to look like; this file runs
each one. The cases live in `tests/fixtures/kit_hooks.json` as data: a hook, a payload,
the exit code it must give and a name. Every bypass a review has found and every false
positive a fix has had to avoid is a row there, so a later change to a pattern cannot
quietly reopen one.

Each case runs twice, once with `jq` as the only parser on PATH and once with `python3`
only, because the hooks carry both and they must agree. The environment is minimal
(`env`-style, `LANG=C.UTF-8`), and the working directory holds a `json.py` that would make
a hook allow everything if a bare `python3 -c` imported it; a case that expects a block
therefore also proves the stub did not run.

A 2 MB payload per hook must finish in under 5 seconds. A hook that outlasts the hook
timeout fails open, so a hang here is a finding, and the subprocess timeout makes it fail
only its own case.
"""

import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLE = json.loads((Path(__file__).parent / "fixtures" / "kit_hooks.json").read_text("utf-8"))

HOOK_FILES = {
    "tf": "refuse-unsaved-terraform-apply",
    "kill": "block-set-based-backend-kill",
    "sup": "require-suppression-reason",
    "sym": "keep-shipped-symbols",
    "erase": "block-whole-device-erase",
    "ddl": "block-destructive-warehouse-ddl",
    "retry": "retry-without-deadline",
    "gen": "generated-stamp-guard",
    "mail": "email-template-unsubscribe",
    "ph": "placeholder-list",
}

# Everything a hook may call besides its parser. A tool a hook starts using that is not here
# fails the whole table, which is the point: the hook has gained a dependency.
BASE_TOOLS = ("bash", "cat", "grep", "sed", "tr", "wc", "head", "awk")

MODES = {"jq": ("jq",), "python3": ("python3",)}

# A json.py that a bare `python3 -c` would import from the working directory. It reports no
# tool input, so a hook that ran it would allow everything; it also leaves a marker file.
STUB_JSON = (
    "import pathlib\n"
    "pathlib.Path('STUB_JSON_RAN').write_text('ran')\n"
    "def load(f):\n"
    "    return {}\n"
    "def dumps(v):\n"
    "    return ''\n"
)

SCRATCH_FILES = {
    "json.py": STUB_JSON,
    "tfplan": "plan",
    "x/tfplan": "plan",
    "applications/bad.md": "Dear team\n[TK: company]\n",
    "applications/-n.md": "[TK: company]\n",
    "applications/good.md": "[TK: company]\n## Placeholders to fill\n- company\n",
    "applications/ok.md": "Dear team\n",
    "applications/dir.md/.keep": "",
    "cv/bad.md": "[TK: role]\n",
}


def _path_for(tool):
    found = shutil.which(tool)
    if tool == "python3" and found is None:
        import sys

        found = sys.executable
    return found


def _missing(tools):
    return [t for t in tools if _path_for(t) is None]


pytestmark = pytest.mark.skipif(
    bool(_missing(BASE_TOOLS)), reason=f"needs {', '.join(_missing(BASE_TOOLS))} on PATH"
)


@pytest.fixture(scope="session")
def scratch(tmp_path_factory):
    cwd = tmp_path_factory.mktemp("kit-hook-cwd")
    for name, text in SCRATCH_FILES.items():
        target = cwd / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    (cwd / "timing").mkdir()
    return cwd


@pytest.fixture(scope="session")
def bins(tmp_path_factory):
    """One directory of symlinks per parser mode, holding exactly the tools a hook may use."""
    made = {}
    for mode, parser in MODES.items():
        if _missing(parser):
            continue
        directory = tmp_path_factory.mktemp(f"bin-{mode}")
        for tool in (*BASE_TOOLS, *parser):
            (directory / tool).symlink_to(_path_for(tool))
        made[mode] = directory
    return made


def _hook_path(key):
    found = sorted(ROOT.glob(f"plugins/*/skills/*/assets/hooks/{HOOK_FILES[key]}.sh"))
    assert len(found) == 1, key
    return found[0]


def _expand(value):
    """Rebuild a large string from `{"parts": [text, [unit, count], ...]}`."""
    if isinstance(value, dict) and "parts" in value:
        return "".join(p if isinstance(p, str) else p[0] * p[1] for p in value["parts"])
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def run_hook(key, stdin, mode, bins, scratch, timeout):
    if mode not in bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    marker = scratch / "STUB_JSON_RAN"
    marker.unlink(missing_ok=True)
    env = {"PATH": str(bins[mode]), "LANG": "C.UTF-8", "HOME": str(scratch)}
    try:
        done = subprocess.run(  # noqa: S603
            [_path_for("bash"), str(_hook_path(key))],
            input=stdin,
            capture_output=True,
            cwd=scratch,
            env=env,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"{HOOK_FILES[key]} ({mode}) did not finish in {timeout} s; "
            "a hook that outlasts its timeout fails open"
        )
    assert not marker.exists(), "the hook imported json.py from the working directory"
    return done


def _stdin(case):
    if "raw" in case:
        return case["raw"].encode("utf-8")
    return json.dumps(_expand(case["payload"]), ensure_ascii=False).encode("utf-8")


def _case_id(case):
    return f"{case['hook']}-{case['name']}"


def test_the_table_covers_every_hook_and_names_are_unique():
    assert set(HOOK_FILES) == {c["hook"] for c in TABLE}
    assert len({_case_id(c) for c in TABLE}) == len(TABLE)
    on_disk = {p.stem for p in ROOT.glob("plugins/*/skills/*/assets/hooks/*.sh")}
    assert on_disk == set(HOOK_FILES.values())


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("case", TABLE, ids=_case_id)
def test_hook_verdict(case, mode, bins, scratch):
    done = run_hook(case["hook"], _stdin(case), mode, bins, scratch, timeout=30)
    assert done.returncode == case["exit"], done.stderr.decode("utf-8", "replace")[:300]
    if case["exit"] == 2:
        assert done.stderr.startswith(b"blocked") or b"placeholder" in done.stderr.lower()


# Worst-case inputs of about 2 MB, built here because they are too large for the table. Each
# is (name, builder, expected exit, files the working directory must hold).
MB = 1_000_000
BIG = {
    "tf": [
        ("one-huge-token", lambda: {"command": "terraform apply " + "x" * (2 * MB)}, 2, {}),
        ("quote-run", lambda: {"command": "terraform apply " + "'" * (2 * MB)}, 2, {}),
        ("many-terraformer-words", lambda: {"command": "terraformer " * 170000}, 0, {}),
        ("no-terraform", lambda: {"command": "echo " + "y" * (2 * MB)}, 0, {}),
    ],
    "kill": [
        (
            "huge-first-argument",
            lambda: {"command": "pg_terminate_backend(" + "x" * (2 * MB)},
            2,
            {},
        ),
        (
            "half-mib-first-argument",
            lambda: {"command": "pg_terminate_backend(" + "x" * 524288 + ")"},
            2,
            {},
        ),
        ("many-calls", lambda: {"command": "select pg_terminate_backend(1);" * 70000}, 2, {}),
        ("name-without-paren", lambda: {"command": "pg_terminate_backend " * 95000}, 2, {}),
        ("no-function", lambda: {"command": "echo " + "x" * (2 * MB)}, 0, {}),
    ],
    "sup": [
        (
            "many-reasoned-markers",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1  # pragma: no mutate because ok\n" * 52000,
            },
            2,
            {},
        ),
        (
            "many-bare-markers",
            lambda: {"file_path": "a.py", "content": "x = 1  # pragma: no mutate\n" * 75000},
            2,
            {},
        ),
        (
            "one-long-marker-line",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1 " + "y" * (2 * MB) + " # pragma: no mutate",
            },
            2,
            {},
        ),
        (
            "many-stryker-markers",
            lambda: {
                "file_path": "a.ts",
                "content": "// Stryker disable next-line all: ok\n" * 55000,
            },
            2,
            {},
        ),
        ("no-marker", lambda: {"file_path": "a.py", "content": "x = 1\n" * 330000}, 0, {}),
    ],
    "sym": [
        (
            "artifact-and-huge-token",
            lambda: {"command": "echo " + "x" * (2 * MB) + " App.dSYM"},
            2,
            {},
        ),
        ("rm-and-huge-token", lambda: {"command": "rm " + "x" * (2 * MB) + " App.dSYM"}, 2, {}),
        ("multibyte-no-artifact", lambda: {"command": "echo " + "é" * MB}, 0, {}),
        ("rm-no-artifact", lambda: {"command": "rm " + "x" * (2 * MB)}, 0, {}),
    ],
    "erase": [
        ("openocd-words", lambda: {"command": "openocd é " * 200000}, 0, {}),
        ("st-flash-words", lambda: {"command": "st-flash é " * 200000}, 0, {}),
        ("commandfile-words", lambda: {"command": "-commandfile x " * 130000}, 0, {}),
        ("erase-words", lambda: {"command": "erase " * 340000}, 0, {}),
        ("erase-pipes", lambda: {"command": "erase | " * 290000}, 0, {}),
        ("jlink-words", lambda: {"command": "JLinkExe " * 220000}, 0, {}),
        (
            "jlink-heredoc-words",
            lambda: {"command": "JLinkExe <<EOF\n" + "connect\n" * 250000},
            0,
            {},
        ),
        ("erase-at-the-end", lambda: {"command": "a " * MB + "&& st-flash erase"}, 2, {}),
        (
            "jlink-erase-at-the-end",
            lambda: {"command": "a\n" * MB + "printf 'r\\nerase\\n' | JLinkExe"},
            2,
            {},
        ),
    ],
    "ddl": [
        ("drop-words", lambda: {"command": "drop " * 400000}, 0, {}),
        ("multibyte-drop-words", lambda: {"command": "drop é " * 300000}, 0, {}),
        ("drop-at-the-end", lambda: {"command": "x " * MB + "DROP TABLE t"}, 2, {}),
    ],
    "retry": [
        (
            "no-match",
            lambda: {"file_path": "a.go", "content": " retr max_ret maxattempt xRetr " * 60000},
            0,
            {},
        ),
        ("multibyte", lambda: {"file_path": "a.go", "content": " retr é max_ret " * 120000}, 0, {}),
        (
            "retry-at-the-end",
            lambda: {"file_path": "a.go", "content": "x " * MB + "retry()"},
            2,
            {},
        ),
    ],
    "gen": [
        (
            "hex-run",
            lambda: {"file_path": "src/generated/v.c", "content": "0123456789abcdef" * 131072},
            0,
            {},
        ),
        (
            "near-sha-runs",
            lambda: {"file_path": "src/generated/v.c", "content": ("a" * 39 + "g") * 52000},
            0,
            {},
        ),
        (
            "near-dates",
            lambda: {"file_path": "src/generated/v.c", "content": "2024-01-0 " * 210000},
            0,
            {},
        ),
        (
            "multibyte",
            lambda: {"file_path": "src/generated/v.c", "content": "abcdef0123é " * 170000},
            0,
            {},
        ),
        (
            "stamp-at-the-end",
            lambda: {
                "file_path": "src/generated/v.c",
                "content": "x " * MB + "2024-01-02T03:04:05",
            },
            2,
            {},
        ),
    ],
    "mail": [
        (
            "near-unsubscribe",
            lambda: {"file_path": "emails/marketing/x.html", "content": "unsubscrib " * 190000},
            2,
            {},
        ),
        (
            "unsubscribe-at-the-end",
            lambda: {"file_path": "emails/marketing/x.html", "content": "x " * MB + "unsubscribe"},
            0,
            {},
        ),
    ],
    "ph": [
        (
            "near-marker",
            lambda: {"file_path": "applications/big-near.md"},
            0,
            {"applications/big-near.md": "[TK " * 500000},
        ),
        (
            "marker-at-the-end",
            lambda: {"file_path": "applications/big-end.md"},
            2,
            {"applications/big-end.md": "x " * MB + "[TK: a]\n"},
        ),
    ],
}

BIG_CASES = [
    pytest.param(key, name, build, want, files, id=f"{key}-{name}")
    for key, items in BIG.items()
    for name, build, want, files in items
]


def test_every_hook_has_a_timing_case():
    assert set(BIG) == set(HOOK_FILES)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(("key", "name", "build", "want", "files"), BIG_CASES)
def test_a_two_megabyte_payload_finishes_in_five_seconds(
    key, name, build, want, files, mode, bins, scratch
):
    for rel, text in files.items():
        (scratch / rel).write_text(text, encoding="utf-8")
    stdin = json.dumps({"tool_input": build()}, ensure_ascii=False).encode("utf-8")
    started = time.monotonic()
    done = run_hook(key, stdin, mode, bins, scratch, timeout=5)
    elapsed = time.monotonic() - started
    assert done.returncode == want, (elapsed, done.stderr.decode("utf-8", "replace")[:300])
    assert elapsed < 5
