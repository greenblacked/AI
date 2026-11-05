"""Behaviour tests for the eleven kit hooks under `plugins/*/skills/*/assets/hooks/`.

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

A large payload per hook must finish in under 5 seconds. A hook that outlasts the hook
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
    "game": "game-data-json",
}

# Everything a hook may call besides its parser. A tool a hook starts using that is not here
# fails the whole table, which is the point: the hook has gained a dependency.
BASE_TOOLS = ("bash", "cat", "grep", "sed", "tr", "wc", "head", "awk")

# A tool only one hook may call, kept out of BASE_TOOLS so that another hook starting to use it
# still fails. `tail` is for game-data-json in its jq mode, which skips a byte order mark with
# `tail -c +4`.
EXTRA_TOOLS = {"game": ("tail",)}

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
    # game-data-json reads the written file; a file outside data/ is invalid on purpose so that
    # an allow proves the hook never opened it.
    "data/valid.json": '{"a": [1, 2]}',
    "data/invalid.json": '{"a": ',
    "data/two.json": "1 2",
    "data/empty.json": "",
    "data/bom.json": '\ufeff{"a": 1}',
    "data/bom-bad.json": '\ufeff{"a": ',
    "data/invalid.txt": "{",
    "other/invalid.json": "{",
    "-x/data/invalid.json": "{",
    "-x/data/valid.json": "{}",
}


def _path_for(tool):
    found = shutil.which(tool)
    if tool == "python3" and found is None:
        import sys

        found = sys.executable
    return found


def _missing(tools):
    return [t for t in tools if _path_for(t) is None]


_ALL_TOOLS = (*BASE_TOOLS, *(t for extra in EXTRA_TOOLS.values() for t in extra))
pytestmark = pytest.mark.skipif(
    bool(_missing(_ALL_TOOLS)), reason=f"needs {', '.join(_missing(_ALL_TOOLS))} on PATH"
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


NORMALISING = ("tf", "kill", "sym", "erase", "ddl")


@pytest.fixture(scope="session")
def bins(tmp_path_factory):
    """One directory of symlinks per parser mode and hook, holding exactly the tools that hook
    may use: the base tools, its parser and whatever EXTRA_TOOLS grants it."""
    made = {}
    for mode, parser in MODES.items():
        if _missing(parser):
            continue
        made[mode] = {}
        for key in HOOK_FILES:
            directory = tmp_path_factory.mktemp(f"bin-{mode}-{key}")
            for tool in (*BASE_TOOLS, *EXTRA_TOOLS.get(key, ()), *parser):
                (directory / tool).symlink_to(_path_for(tool))
            made[mode][key] = directory
    return made


@pytest.fixture(scope="session")
def noawk_bins(tmp_path_factory):
    """Like `bins`, for the hooks that normalise the command with awk, but with no awk."""
    made = {}
    for mode, parser in MODES.items():
        if _missing(parser):
            continue
        made[mode] = {}
        for key in NORMALISING:
            directory = tmp_path_factory.mktemp(f"bin-noawk-{mode}-{key}")
            for tool in (*(t for t in BASE_TOOLS if t != "awk"), *parser):
                (directory / tool).symlink_to(_path_for(tool))
            made[mode][key] = directory
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
    env = {"PATH": str(bins[mode][key]), "LANG": "C.UTF-8", "HOME": str(scratch)}
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


def test_extra_tools_stay_with_the_hook_that_needs_them(bins):
    assert set(EXTRA_TOOLS) <= set(HOOK_FILES)
    for per_hook in bins.values():
        for key, directory in per_hook.items():
            for tool in {t for extra in EXTRA_TOOLS.values() for t in extra}:
                granted = tool in EXTRA_TOOLS.get(key, ())
                assert (directory / tool).exists() == granted, (key, tool)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("case", TABLE, ids=_case_id)
def test_hook_verdict(case, mode, bins, scratch):
    done = run_hook(case["hook"], _stdin(case), mode, bins, scratch, timeout=30)
    assert done.returncode == case["exit"], done.stderr.decode("utf-8", "replace")[:300]
    if case["exit"] == 2:
        assert (
            done.stderr.startswith(b"blocked")
            or b"placeholder" in done.stderr.lower()
            or b"invalid JSON" in done.stderr
        )


# Without awk the normalising hooks cannot read the command. Left alone they would exit 127,
# which is not a block, so the command would run unjudged; they refuse with exit 2 instead,
# whatever the command is.
NO_AWK_COMMANDS = {
    "tf": ("terraform apply -auto-approve", "terraform plan"),
    "kill": ("select pg_terminate_backend(pid)", "select 1"),
    "sym": ("rm App.dSYM", "ls build"),
    "erase": ("st-flash erase", "ls build"),
    "ddl": ("DROP TABLE t", "select 1"),
}


def test_no_awk_case_for_every_normalising_hook():
    assert set(NO_AWK_COMMANDS) == set(NORMALISING)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("key", "command"),
    [(k, c) for k in NORMALISING for c in NO_AWK_COMMANDS[k]],
    ids=lambda v: v if v in NORMALISING else v.replace(" ", "_"),
)
def test_a_missing_awk_refuses(key, command, mode, noawk_bins, scratch):
    if mode not in noawk_bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    assert not (noawk_bins[mode][key] / "awk").exists()
    stdin = json.dumps({"tool_input": {"command": command}}).encode("utf-8")
    done = run_hook(key, stdin, mode, noawk_bins, scratch, timeout=30)
    assert done.returncode == 2, done.stderr.decode("utf-8", "replace")[:300]
    assert done.stderr.startswith(b"blocked")
    assert b"awk" in done.stderr


# A call with no command to judge (a tool other than Bash, or a null command) must not fail for
# want of awk: the guard above is for a command that would run unjudged, and there is none.
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("key", NORMALISING)
@pytest.mark.parametrize(
    "payload",
    [{"tool_input": {"command": None}}, {"tool_input": {}}, {}, {"tool_input": {"command": ""}}],
    ids=["null-command", "no-command", "no-tool-input", "empty-command"],
)
def test_no_command_is_allowed_without_awk(key, payload, mode, noawk_bins, scratch):
    if mode not in noawk_bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    done = run_hook(key, json.dumps(payload).encode("utf-8"), mode, noawk_bins, scratch, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")[:300]


def _function_body(path, name):
    text = path.read_text("utf-8")
    start = text.index(f"\n{name}() {{\n") + 1
    return text[start : text.index("\n}\n", start) + 3]


def test_the_normalise_function_is_the_same_in_every_hook_that_has_one():
    bodies = {key: _function_body(_hook_path(key), "normalise") for key in NORMALISING}
    assert len(set(bodies.values())) == 1, {k: v for k, v in bodies.items()}
    assert "LC_ALL=C awk" in bodies["tf"]


def test_openocd_erase_address_is_refused_as_a_range_not_a_whole_device(bins, scratch):
    command = "openocd -c 'flash erase_address 0x08000000 0x100000'"
    stdin = json.dumps({"tool_input": {"command": command}}).encode("utf-8")
    for mode in MODES:
        done = run_hook("erase", stdin, mode, bins, scratch, timeout=30)
        assert done.returncode == 2
        assert b"erase_address" in done.stderr
        assert b"range" in done.stderr
        assert b"whole-device" not in done.stderr


# Worst-case inputs of about 2 MB, built here because they are too large for the table. Each
# is (name, builder, expected exit, files the working directory must hold).
MB = 1_000_000
BIG = {
    "tf": [
        # A command made of continuation lines is joined into one line; joining by appending to a
        # buffer is quadratic in the number of lines.
        ("continuation-lines", lambda: {"command": "terraform plan \\\n" * 100000}, 2, {}),
        ("one-huge-token", lambda: {"command": "terraform apply " + "x" * (2 * MB)}, 2, {}),
        ("quote-run", lambda: {"command": "terraform apply " + "'" * (2 * MB)}, 2, {}),
        ("many-terraformer-words", lambda: {"command": "terraformer " * 170000}, 0, {}),
        ("no-terraform", lambda: {"command": "echo " + "y" * (2 * MB)}, 0, {}),
    ],
    "kill": [
        ("continuation-lines", lambda: {"command": "echo \\\n" * 300000}, 0, {}),
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
    # Each stays under the 1 MiB the hook refuses at, so the time is the awk pass over the text and
    # not the refusal; test_the_sup_timing_rows_reach_the_awk_pass checks that.
    "sup": [
        (
            "many-reasoned-markers",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1  # pragma: no mutate because ok\n" * 25000,
            },
            0,
            {},
        ),
        (
            "many-bare-markers",
            lambda: {"file_path": "a.py", "content": "x = 1  # pragma: no mutate\n" * 36000},
            2,
            {},
        ),
        (
            "one-long-marker-line",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1 " + "y" * 900000 + " # pragma: no mutate",
            },
            2,
            {},
        ),
        (
            "many-stryker-markers",
            lambda: {
                "file_path": "a.ts",
                "content": "// Stryker disable next-line all: ok\n" * 27000,
            },
            0,
            {},
        ),
        (
            "many-multibyte-reasons",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1  # pragma: no mutate \u7b49\u4fa1\u5909\u7570 \u2026\n" * 20000,
            },
            0,
            {},
        ),
        (
            "oversized-refusal",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1  # pragma: no mutate because ok\n" * 28000,
            },
            2,
            {},
        ),
        ("no-marker", lambda: {"file_path": "a.py", "content": "x = 1\n" * 330000}, 0, {}),
    ],
    "sym": [
        ("continuation-lines", lambda: {"command": "echo App.dSYM \\\n" * 100000}, 2, {}),
        (
            "artifact-and-huge-token",
            lambda: {"command": "echo " + "x" * (2 * MB) + " App.dSYM"},
            2,
            {},
        ),
        ("rm-and-huge-token", lambda: {"command": "rm " + "x" * (2 * MB) + " App.dSYM"}, 2, {}),
        ("multibyte-no-artifact", lambda: {"command": "echo " + "é" * MB}, 0, {}),
        ("rm-no-artifact", lambda: {"command": "rm " + "x" * (2 * MB)}, 0, {}),
        ("escape-and-brace-runs", lambda: {"command": "echo $'\\x41'{a,b} " * 100000}, 0, {}),
        ("escape-and-near-dsym-runs", lambda: {"command": "echo $'\\x41'dsy " * 100000}, 0, {}),
    ],
    "erase": [
        ("continuation-lines", lambda: {"command": "st-flash read \\\n" * 100000}, 0, {}),
        ("openocd-words", lambda: {"command": "openocd é " * 200000}, 0, {}),
        ("st-flash-words", lambda: {"command": "st-flash é " * 200000}, 0, {}),
        ("commandfile-words", lambda: {"command": "-commandfile x " * 130000}, 0, {}),
        ("erase-words", lambda: {"command": "erase " * 340000}, 0, {}),
        ("erase-pipes", lambda: {"command": "erase | " * 290000}, 0, {}),
        ("jlink-words", lambda: {"command": "JLinkExe " * 220000}, 0, {}),
        ("jlink-words-with-carriage-returns", lambda: {"command": "JLinkExe\r\n" * 200000}, 0, {}),
        (
            "jlink-heredoc-words",
            lambda: {"command": "JLinkExe <<EOF\n" + "connect\n" * 250000},
            0,
            {},
        ),
        ("erase-at-the-end", lambda: {"command": "a " * MB + "&& st-flash erase"}, 2, {}),
        # Every heredoc, and every echo, writes `erase` to its own file and thousands of other
        # lines name J-Link, so comparing each file with each J-Link line is quadratic in the
        # input. The last row names the very last file, so the answer is found only at the end.
        (
            "heredoc-files-times-jlink-lines",
            lambda: {
                "command": "".join(f"cat <<E > f{i}\nerase\nE\n" for i in range(40000))
                + "jlink x\n" * 70000
            },
            0,
            {},
        ),
        (
            "writer-files-times-jlink-lines",
            lambda: {
                "command": "".join(f"echo erase > f{i}\n" for i in range(60000))
                + "jlink x\n" * 70000
            },
            0,
            {},
        ),
        (
            "writer-files-times-jlink-lines-named-at-the-end",
            lambda: {
                "command": "".join(f"echo erase > f{i}\n" for i in range(60000))
                + "jlink x\n" * 70000
                + "JLinkExe -CommandFile f59999"
            },
            2,
            {},
        ),
        # Under a UTF-8 locale GNU grep took quadratic time on the stdin patterns for this shape: a
        # word `erase` that is not alone before the `;`, and tens of thousands of J-Link commands.
        (
            "erase-argument-then-many-jlink-commands",
            lambda: {"command": "echo erase x; " + "JLinkExe -x f; " * 20000},
            0,
            {},
        ),
        (
            "many-jlink-lines-one-file",
            lambda: {"command": "echo erase > f\n" + "jlink x\n" * 200000},
            0,
            {},
        ),
        (
            "many-redirects-on-one-heredoc-line",
            lambda: {"command": "cat <<E" + " >f" * 300000 + "\nconnect\nE\njlink f"},
            0,
            {},
        ),
        (
            "jlink-erase-at-the-end",
            lambda: {"command": "a\n" * MB + "printf 'r\\nerase\\n' | JLinkExe"},
            2,
            {},
        ),
    ],
    "ddl": [
        ("continuation-lines", lambda: {"command": "echo \\\n" * 300000}, 0, {}),
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
    "game": [
        (
            "big-valid-array",
            lambda: {"file_path": "data/big-valid.json"},
            0,
            {"data/big-valid.json": "[" + "1," * MB + "1]"},
        ),
        (
            "big-many-values",
            lambda: {"file_path": "data/big-many.json"},
            2,
            {"data/big-many.json": "1 " * MB},
        ),
        (
            "big-bom-invalid-at-the-end",
            lambda: {"file_path": "data/big-bom.json"},
            2,
            {"data/big-bom.json": "\ufeff[" + "1," * MB + "]"},
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

# A match on the first line of a multi-line input, followed by more than a pipe buffer of further
# lines. `grep -q` quits at the match and a writer piped into it dies of SIGPIPE, which `pipefail`
# turns into a failed pipeline; a hook that read that as "no match" allowed the command.
LINES = "echo padding line here\n" * 40000
EARLY = {
    "tf": [
        (
            "violation-first-line",
            lambda: {"command": "terraform apply -auto-approve\n" + LINES},
            2,
            {},
        )
    ],
    "kill": [
        (
            "violation-first-line",
            lambda: {"command": "select pg_terminate_backend(pid)\n" + LINES},
            2,
            {},
        )
    ],
    "sup": [
        (
            "violation-first-line",
            lambda: {"file_path": "a.py", "content": "x = 1  # pragma: no mutate\n" + LINES},
            2,
            {},
        )
    ],
    "sym": [("violation-first-line", lambda: {"command": "rm App.dSYM\n" + LINES}, 2, {})],
    "erase": [("violation-first-line", lambda: {"command": "st-flash erase\n" + LINES}, 2, {})],
    "ddl": [("violation-first-line", lambda: {"command": "DROP TABLE t\n" + LINES}, 2, {})],
    "retry": [
        (
            "violation-first-line",
            lambda: {"file_path": "a.go", "content": "retry()\n" + LINES},
            2,
            {},
        ),
    ],
    "gen": [
        (
            "violation-first-line",
            lambda: {"file_path": "src/generated/v.c", "content": "2024-01-02T03:04:05\n" + LINES},
            2,
            {},
        )
    ],
    "mail": [
        (
            "unsubscribe-first-line",
            lambda: {"file_path": "emails/marketing/x.html", "content": "unsubscribe\n" + LINES},
            0,
            {},
        )
    ],
    "game": [
        (
            "invalid-after-a-long-first-line",
            lambda: {"file_path": "data/early.json"},
            2,
            {"data/early.json": "{" + LINES},
        )
    ],
    "ph": [
        (
            "tk-first-line",
            lambda: {"file_path": "applications/big-first.md"},
            2,
            {"applications/big-first.md": "[TK: a]\n" + LINES},
        )
    ],
}
for _key, _items in EARLY.items():
    BIG[_key] = BIG[_key] + _items

BIG_CASES = [
    pytest.param(key, name, build, want, files, id=f"{key}-{name}")
    for key, items in BIG.items()
    for name, build, want, files in items
]


SUP_LIMIT = 1024 * 1024


def test_the_sup_timing_rows_reach_the_awk_pass():
    """A timing row that hits the size refusal measures nothing about the scan. Every row that
    holds a marker is below the limit, except the refusal row; the row without a marker never
    reaches the refusal, whatever its size."""
    for name, build, _, _ in BIG["sup"]:
        if name == "no-marker":
            continue
        size = len(build()["content"].encode("utf-8"))
        assert (size > SUP_LIMIT) == (name == "oversized-refusal"), (name, size)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", ["many-bare-markers", "one-long-marker-line"])
def test_a_large_bare_marker_is_judged_not_refused(name, mode, bins, scratch):
    build = {n: b for n, b, _, _ in BIG["sup"]}[name]
    stdin = json.dumps({"tool_input": build()}, ensure_ascii=False).encode("utf-8")
    done = run_hook("sup", stdin, mode, bins, scratch, timeout=5)
    assert done.returncode == 2
    assert b"needs a reason" in done.stderr
    assert b"larger than" not in done.stderr


# A payload per hook that is innocent (or, for tf and sym, at least not decided before the first
# grep) and larger than the 64 KiB bash keeps in a pipe for a here-string, so the here-string goes
# through a temporary file. With the file-size limit at 1 KiB that write fails, the redirection
# fails with status 1, and grep never runs. A hook that read that status as "no match" would allow
# the command; each must refuse with exit 2 instead. placeholder-list reads a file and has no
# here-string.
HUGE = 100_000
NO_SCAN = {
    "tf": lambda: {"command": "terraform plan " + "x" * HUGE},
    "kill": lambda: {"command": "echo " + "x" * HUGE},
    "sup": lambda: {"file_path": "a.py", "content": "# pragma: no mutate ok\n" + "x = 1\n" * 20000},
    "sym": lambda: {"command": "echo " + "x" * HUGE},
    "erase": lambda: {"command": "echo " + "x" * HUGE},
    "ddl": lambda: {"command": "echo " + "x" * HUGE},
    "retry": lambda: {"file_path": "a.go", "content": "x = 1\n" * 20000},
    "gen": lambda: {"file_path": "src/generated/v.c", "content": "x = 1\n" * 20000},
    "mail": lambda: {"file_path": "emails/marketing/x.html", "content": "x = 1\n" * 20000},
}


def test_no_scan_case_for_every_hook_with_a_here_string():
    assert set(NO_SCAN) == set(HOOK_FILES) - {"ph", "game"}


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("key", sorted(NO_SCAN))
def test_a_here_string_that_cannot_be_written_refuses(key, mode, bins, scratch):
    if mode not in bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    stdin = json.dumps({"tool_input": NO_SCAN[key]()}, ensure_ascii=False).encode("utf-8")
    env = {"PATH": str(bins[mode][key]), "LANG": "C.UTF-8", "HOME": str(scratch)}
    # ulimit -f is in 1 KiB units; ignoring SIGXFSZ turns the over-limit write into an error
    # instead of killing bash, which is what a full disk gives.
    script = 'ulimit -f 1; trap "" XFSZ; exec "$0" "$1"'
    done = subprocess.run(  # noqa: S603
        [_path_for("bash"), "-c", script, _path_for("bash"), str(_hook_path(key))],
        input=stdin,
        capture_output=True,
        cwd=scratch,
        env=env,
        timeout=30,
        check=False,
    )
    assert done.returncode == 2, done.stderr.decode("utf-8", "replace")[-300:]
    assert b"blocked: could not scan" in done.stderr


def test_every_hook_has_a_timing_case():
    assert set(BIG) == set(HOOK_FILES)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(("key", "name", "build", "want", "files"), BIG_CASES)
def test_a_large_payload_finishes_in_five_seconds(
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
