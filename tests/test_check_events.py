"""The audio event checker: table against code, each finding code, and how it exits."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/gamedev/skills/game-audio-event-spec/scripts/check_events.py"

spec = importlib.util.spec_from_file_location("check_events", SCRIPT)
assert spec is not None
assert spec.loader is not None
events = importlib.util.module_from_spec(spec)
sys.modules["check_events"] = events
spec.loader.exec_module(events)

HEADER = "id,trigger,variants,bus,priority,max_instances,steal,duck_group,spatial\n"


def row(eid: str, **over: str) -> str:
    cols = {
        "trigger": "on step",
        "variants": "4",
        "bus": "sfx",
        "priority": "50",
        "max_instances": "4",
        "steal": "oldest",
        "duck_group": "none",
        "spatial": "3d",
    }
    cols.update(over)
    return ",".join([eid, *cols.values()]) + "\n"


def run(
    tmp_path: Path,
    table: str,
    code: dict[str, str],
    capsys: pytest.CaptureFixture[str],
    *extra: str,
) -> tuple[int, list[str]]:
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(table, encoding="utf-8")
    src = tmp_path / "src"
    for name, text in code.items():
        target = src / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    src.mkdir(exist_ok=True)
    rc = events.main([str(csv_path), str(src), *extra])
    return rc, capsys.readouterr().out.splitlines()


def test_matching_table_and_code_is_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(
        tmp_path,
        HEADER + row("sfx.player.step"),
        {"player.gd": 'audio.play("sfx.player.step")\n'},
        capsys,
    )
    assert rc == 0
    assert out == []


def test_used_but_missing_and_unused_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(
        tmp_path,
        HEADER + row("sfx.player.step") + row("sfx.player.jump"),
        {"a.cs": 'Play("sfx.player.step"); Play("sfx.door.slam");\n'},
        capsys,
    )
    assert rc == 1
    assert any(ln.startswith("sfx.door.slam: missing-from-table: used at") for ln in out)
    assert "sfx.player.jump: unused-row: no string literal in the code tree names it" in out


def test_ordinary_dotted_strings_with_other_prefixes_are_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(
        tmp_path,
        HEADER + row("sfx.player.step"),
        {"a.py": 'x = "sfx.player.step"\nname = "readme.txt"\nv = "1.2.3"\n'},
        capsys,
    )
    assert rc == 0, out


def test_extra_prefix_flag_catches_ids_with_a_new_prefix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(
        tmp_path,
        HEADER + row("sfx.player.step"),
        {"a.py": 'a = "sfx.player.step"\nb = "mus.menu.theme"\n'},
        capsys,
        "--prefix",
        "mus",
    )
    assert rc == 1
    assert any(ln.startswith("mus.menu.theme: missing-from-table") for ln in out)


def test_skipped_directories_and_extensions_are_not_scanned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(
        tmp_path,
        HEADER + row("sfx.player.step"),
        {
            "a.gd": '"sfx.player.step"\n',
            "node_modules/x.js": '"sfx.ghost.one"\n',
            "notes.md": '"sfx.ghost.two"\n',
        },
        capsys,
    )
    assert rc == 0, out


def test_table_findings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    table = (
        HEADER
        + row("sfx.a.one")
        + row("sfx.a.one")
        + row("sfx.a.two", max_instances="many", spatial="4d", steal="random", bus="")
        + row("SFX Bad")
    )
    rc, out = run(tmp_path, table, {"a.gd": '"sfx.a.one" "sfx.a.two"\n'}, capsys)
    assert rc == 1
    assert "sfx.a.one: duplicate-id: appears more than once in the table" in out
    assert "sfx.a.two: empty-field: bus is empty" in out
    assert "sfx.a.two: bad-value: max_instances is not a whole number" in out
    assert "sfx.a.two: bad-value: spatial must be 2d or 3d" in out
    assert any(ln.startswith("sfx.a.two: bad-value: steal must be one of") for ln in out)
    assert "SFX Bad: bad-value: id is not dotted lowercase" in out


def test_header_missing_columns_exits_with_a_message(tmp_path: Path) -> None:
    csv_path = tmp_path / "events.csv"
    csv_path.write_text("id,bus\nsfx.a.b,sfx\n", encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        events.read_table(str(csv_path))
    assert "header lacks columns" in str(caught.value)
