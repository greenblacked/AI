"""The game-builder kit hook: a JSON file with a BOM loads fine and must not be reported."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "plugins/gamedev/skills/game-builder/assets/hooks/game-data-json.sh"
BOM = b"\xef\xbb\xbf"


def tool_dir(tmp_path: Path, names: list[str], name: str) -> Path:
    """A PATH holding only the named tools, so one parser can be left out on purpose."""
    d = tmp_path / name
    d.mkdir()
    for tool in names:
        found = shutil.which(tool)
        if found is None:
            pytest.skip(f"{tool} is not installed")
        (d / tool).symlink_to(Path(found).resolve())
    return d


def run_hook(path_dir: Path, target: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"file_path": str(target)}})
    env = {"PATH": str(path_dir), "LC_ALL": "C"}
    bash = shutil.which("bash")
    assert bash is not None
    return subprocess.run(  # noqa: S603 - fixed argv and the repository's own hook, test only
        [bash, str(HOOK)], input=payload, text=True, capture_output=True, env=env, check=False
    )


@pytest.fixture(params=["python", "jq"])
def mode_dir(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    # python mode: no jq on PATH. jq mode: no python3, so jq both finds the path and parses.
    if request.param == "python":
        return tool_dir(tmp_path, ["cat", "python3"], "py")
    return tool_dir(tmp_path, ["cat", "jq", "sed"], "jq")


def data_file(tmp_path: Path, content: bytes) -> Path:
    d = tmp_path / "proj" / "data"
    d.mkdir(parents=True)
    f = d / "items.json"
    f.write_bytes(content)
    return f


def test_valid_file_passes(mode_dir: Path, tmp_path: Path) -> None:
    result = run_hook(mode_dir, data_file(tmp_path, b'{"a": 1}'))
    assert result.returncode == 0, result.stderr


def test_valid_file_with_a_bom_passes(mode_dir: Path, tmp_path: Path) -> None:
    result = run_hook(mode_dir, data_file(tmp_path, BOM + b'{"a": 1}'))
    assert result.returncode == 0, result.stderr


def test_invalid_file_is_reported(mode_dir: Path, tmp_path: Path) -> None:
    result = run_hook(mode_dir, data_file(tmp_path, b'{"a": '))
    assert result.returncode == 2
    assert "invalid JSON" in result.stderr


def test_invalid_file_with_a_bom_is_still_reported(mode_dir: Path, tmp_path: Path) -> None:
    result = run_hook(mode_dir, data_file(tmp_path, BOM + b'{"a": '))
    assert result.returncode == 2
