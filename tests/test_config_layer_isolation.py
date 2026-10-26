"""The suite never reads the app, host or user configuration layer of the machine it runs on.

A host with the CLI deployed system-wide (``/etc/xdg/<slug>/`` on Linux, ``/Library/Application
Support/<vendor>/<app>/`` on macOS, ``C:\\ProgramData\\<vendor>\\<app>\\`` on Windows) would
otherwise decide test results: a ``config.d/99-*.toml`` setting a value there makes tests fail on
that machine while a clean CI runner stays green. These tests ask lib_layered_config where those
layers live, with the code its deploy and its reader share, rather than inspecting the
environment variables the conftest sets.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from lib_layered_config import deploy_config_paths

from igittigitt import __init__conf__
from igittigitt.adapters.config.loader import get_config, get_default_config_path

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: The fixtures that keep the machine's configuration layers out of a test.
_LAYER_REDIRECTS = frozenset({"system_layers_in_tmp_path", "user_layer_in_tmp_path"})

#: A pytest plugin writing the fixtures each collected doctest gets. ``--fixtures-per-test`` would
#: answer this directly, but it crashes on doctest items (pytest 9.1: DoctestItem has no ``function``).
_DOCTEST_FIXTURE_REPORT_PLUGIN = """\
import json
import os

import pytest


def pytest_collection_modifyitems(items):
    report = {
        item.nodeid: sorted(item.fixturenames) for item in items if isinstance(item, pytest.DoctestItem)
    }
    with open(os.environ["DOCTEST_FIXTURE_REPORT"], "w", encoding="utf-8") as report_file:
        json.dump(report, report_file)
"""


@pytest.mark.os_agnostic
@pytest.mark.parametrize("target", ["app", "host", "user"])
def test_every_config_layer_resolves_inside_the_test_s_own_directory(target: str, tmp_path: Path) -> None:
    paths = deploy_config_paths(
        get_default_config_path(),
        vendor=__init__conf__.LAYEREDCONF_VENDOR,
        app=__init__conf__.LAYEREDCONF_APP,
        slug=__init__conf__.LAYEREDCONF_SLUG,
        targets=[target],
    )
    outside = sorted(path for path in paths if not path.is_relative_to(tmp_path.resolve()))

    assert outside == [], f"the {target} layer resolves outside this test's directory: {outside}"


@pytest.mark.os_agnostic
def test_a_file_in_the_redirected_app_layer_is_what_the_loader_reads(
    app_layer_config_file: Path, clear_config_cache: None
) -> None:
    app_layer_config_file.write_text('[layer_isolation_probe]\nread_from = "redirected app layer"\n', encoding="utf-8")

    config = get_config()

    assert config.get("layer_isolation_probe.read_from") == "redirected app layer"


@pytest.mark.os_agnostic
def test_a_file_in_the_redirected_user_layer_is_what_the_loader_reads(
    user_layer_config_file: Path, clear_config_cache: None
) -> None:
    user_layer_config_file.write_text(
        '[layer_isolation_probe]\nread_from = "redirected user layer"\n', encoding="utf-8"
    )

    config = get_config()

    assert config.get("layer_isolation_probe.read_from") == "redirected user layer"


@pytest.mark.os_agnostic
def test_every_doctest_collected_from_src_gets_the_layer_redirects(tmp_path: Path) -> None:
    """``--doctest-modules`` collects ``src/`` too; a fixture in ``tests/conftest.py`` would not reach it."""
    (tmp_path / "_doctest_fixture_report.py").write_text(_DOCTEST_FIXTURE_REPORT_PLUGIN, encoding="utf-8")
    report_file = tmp_path / "doctest-fixtures.json"
    python_path = os.pathsep.join(filter(None, [str(tmp_path), os.environ.get("PYTHONPATH", "")]))
    env = {**os.environ, "PYTHONPATH": python_path, "DOCTEST_FIXTURE_REPORT": str(report_file)}
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"]
    completed = subprocess.run(
        [*command, "-p", "_doctest_fixture_report", "src"],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report: dict[str, list[str]] = json.loads(report_file.read_text(encoding="utf-8"))
    assert report, "no doctest was collected from src/, so this test checks nothing"

    unredirected = {node: names for node, names in report.items() if not set(names) >= _LAYER_REDIRECTS}

    assert unredirected == {}, f"{len(unredirected)} of {len(report)} doctests run against the machine's layers"
