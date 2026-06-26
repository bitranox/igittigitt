"""Package metadata and PEP 561 marker tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import rtoml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


def _load_pyproject() -> dict[str, Any]:
    """Load and parse pyproject.toml from the project root."""
    return rtoml.load(PYPROJECT_PATH)


def _get_package_dir() -> Path:
    """Locate the package directory based on pyproject.toml configuration."""
    pyproject = _load_pyproject()
    project_table = cast(dict[str, Any], pyproject["project"])
    tool_table = cast(dict[str, Any], pyproject.get("tool", {}))
    hatch_table = cast(dict[str, Any], tool_table.get("hatch", {}))
    targets_table = cast(dict[str, Any], cast(dict[str, Any], hatch_table.get("build", {})).get("targets", {}))
    wheel_table = cast(dict[str, Any], targets_table.get("wheel", {}))
    packages = cast(list[Any], wheel_table.get("packages", []))

    for package_entry in packages:
        if isinstance(package_entry, str):
            candidate = PROJECT_ROOT / package_entry
            if candidate.is_dir():
                return candidate

    fallback = PROJECT_ROOT / "src" / project_table["name"].replace("-", "_")
    if fallback.is_dir():
        return fallback

    raise AssertionError("Unable to locate package directory")


@pytest.mark.os_agnostic
def test_when_print_info_runs_it_outputs_metadata(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify print_info outputs package metadata."""
    from igittigitt import print_info

    print_info()

    captured = capsys.readouterr().out
    assert "igittigitt" in captured
    assert "version" in captured


@pytest.mark.os_agnostic
def test_metadata_constants_are_set() -> None:
    """Verify static metadata constants are properly set."""
    from igittigitt import __init__conf__

    # These should be non-empty when package is installed
    assert __init__conf__.name == "igittigitt"
    assert __init__conf__.version  # Should have a version
    assert __init__conf__.shell_command == "igittigitt"


@pytest.mark.os_agnostic
def test_py_typed_marker_exists() -> None:
    """Verify PEP 561 py.typed marker exists in the package source."""
    package_dir = _get_package_dir()
    py_typed = package_dir / "py.typed"
    assert py_typed.is_file(), f"PEP 561 marker not found at {py_typed}"


@pytest.mark.os_agnostic
def test_py_typed_marker_included_in_wheel_config() -> None:
    """Verify py.typed is listed in wheel build includes."""
    pyproject = _load_pyproject()
    tool_table = cast(dict[str, Any], pyproject.get("tool", {}))
    hatch_table = cast(dict[str, Any], tool_table.get("hatch", {}))
    build_table = cast(dict[str, Any], hatch_table.get("build", {}))
    targets_table = cast(dict[str, Any], build_table.get("targets", {}))
    wheel_table = cast(dict[str, Any], targets_table.get("wheel", {}))
    includes = cast(list[str], wheel_table.get("include", []))
    assert any("py.typed" in entry for entry in includes), "py.typed must be in wheel build includes"
