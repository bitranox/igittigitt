"""CLI tests: info, version, help, module entry, and the check/filter commands."""

from __future__ import annotations

import runpy
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner

from igittigitt import __init__conf__
from igittigitt.adapters.cli import cli, main
from igittigitt.adapters.cli.exit_codes import ExitCode
from igittigitt.composition import build_production

_SRC_DIR = str(Path(__file__).resolve().parents[1] / "src")

Factory = Callable[[], object]


def _subprocess_env() -> dict[str, str]:
    import os

    existing = os.environ.get("PYTHONPATH", "")
    pythonpath = f"{_SRC_DIR}{os.pathsep}{existing}" if existing else _SRC_DIR
    return {**os.environ, "PYTHONPATH": pythonpath}


@pytest.mark.os_agnostic
def test_help_is_shown_without_subcommand(cli_runner: CliRunner, production_factory: Factory) -> None:
    result = cli_runner.invoke(cli, [], obj=production_factory)
    assert result.exit_code == 0
    assert "Usage:" in result.output


@pytest.mark.os_agnostic
def test_version_outputs_version(cli_runner: CliRunner, production_factory: Factory) -> None:
    result = cli_runner.invoke(cli, ["--version"], obj=production_factory)
    assert result.exit_code == 0
    assert __init__conf__.version in result.output


@pytest.mark.os_agnostic
def test_info_displays_metadata(cli_runner: CliRunner, production_factory: Factory) -> None:
    result = cli_runner.invoke(cli, ["info"], obj=production_factory)
    assert result.exit_code == 0
    assert f"Info for {__init__conf__.name}:" in result.output
    assert __init__conf__.version in result.output


@pytest.mark.os_agnostic
def test_unknown_command_errors(cli_runner: CliRunner, production_factory: Factory) -> None:
    result = cli_runner.invoke(cli, ["does-not-exist"], obj=production_factory)
    assert result.exit_code != 0
    assert "No such command" in result.output


@pytest.mark.os_agnostic
def test_main_returns_zero_for_help() -> None:
    assert main(["--help"], services_factory=build_production) == 0


@pytest.mark.os_agnostic
def test_module_entry_subprocess_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "igittigitt", "--version"],
        capture_output=True,
        timeout=30,
        check=False,
        encoding="utf-8",
        errors="replace",
        env=_subprocess_env(),
    )
    assert result.returncode == 0
    assert __init__conf__.version in result.stdout


@pytest.mark.os_agnostic
def test_module_entry_runpy_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["igittigitt"], raising=False)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("igittigitt.__main__", run_name="__main__")
    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert "Usage:" in captured.out


# --- check command -----------------------------------------------------------


def _make_tree(tmp_path: Path) -> Path:
    (tmp_path / ".gitignore").write_text("*.log\nbuild/\n!build/keep.log\n", encoding="utf-8")
    (tmp_path / "a.log").touch()
    (tmp_path / "a.txt").touch()
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "out.o").touch()
    (tmp_path / "build" / "keep.log").touch()
    return tmp_path


@pytest.mark.os_agnostic
def test_check_reports_ignored_paths(cli_runner: CliRunner, production_factory: Factory, tmp_path: Path) -> None:
    _make_tree(tmp_path)
    result = cli_runner.invoke(
        cli, ["check", "-C", str(tmp_path), "a.log", "a.txt", "build/out.o"], obj=production_factory
    )
    out_lines = set(result.output.split())
    assert "a.log" in out_lines
    assert "build/out.o" in out_lines
    assert "a.txt" not in out_lines
    assert result.exit_code == ExitCode.SUCCESS


@pytest.mark.os_agnostic
def test_check_exit_one_when_nothing_ignored(
    cli_runner: CliRunner, production_factory: Factory, tmp_path: Path
) -> None:
    _make_tree(tmp_path)
    result = cli_runner.invoke(cli, ["check", "-C", str(tmp_path), "a.txt"], obj=production_factory)
    assert result.exit_code == ExitCode.GENERAL_ERROR
    assert result.stdout.strip() == ""


@pytest.mark.os_agnostic
def test_check_reads_stdin(cli_runner: CliRunner, production_factory: Factory, tmp_path: Path) -> None:
    _make_tree(tmp_path)
    result = cli_runner.invoke(
        cli, ["check", "-C", str(tmp_path), "--stdin"], input="a.log\na.txt\n", obj=production_factory
    )
    assert result.stdout.split() == ["a.log"]


@pytest.mark.os_agnostic
def test_check_verbose_shows_pattern(cli_runner: CliRunner, production_factory: Factory, tmp_path: Path) -> None:
    _make_tree(tmp_path)
    result = cli_runner.invoke(cli, ["check", "-C", str(tmp_path), "-v", "a.log"], obj=production_factory)
    assert ".gitignore" in result.output
    assert "*.log" in result.output
    assert "\ta.log" in result.output


# --- filter command ----------------------------------------------------------


@pytest.mark.os_agnostic
def test_filter_drops_ignored(cli_runner: CliRunner, production_factory: Factory, tmp_path: Path) -> None:
    _make_tree(tmp_path)
    result = cli_runner.invoke(
        cli, ["filter", "-C", str(tmp_path)], input="a.log\na.txt\nbuild/out.o\n", obj=production_factory
    )
    assert result.stdout.split() == ["a.txt"]


@pytest.mark.os_agnostic
def test_filter_include_mode_keeps_matches(cli_runner: CliRunner, production_factory: Factory, tmp_path: Path) -> None:
    result = cli_runner.invoke(
        cli,
        ["filter", "-C", str(tmp_path), "--include", "-r", "*.py"],
        input="keep.py\ndrop.txt\nsub/deep.py\n",
        obj=production_factory,
    )
    assert set(result.stdout.split()) == {"keep.py", "sub/deep.py"}


@pytest.mark.os_agnostic
def test_filter_zero_separated(cli_runner: CliRunner, production_factory: Factory, tmp_path: Path) -> None:
    _make_tree(tmp_path)
    result = cli_runner.invoke(
        cli, ["filter", "-C", str(tmp_path), "-z"], input="a.log\0a.txt\0", obj=production_factory
    )
    assert result.stdout.split("\0") == ["a.txt", ""]


@pytest.mark.os_agnostic
def test_filter_rejects_separatorless_giant_token(
    cli_runner: CliRunner, production_factory: Factory, tmp_path: Path
) -> None:
    """A huge separator-less stream is rejected, not buffered unbounded (bounded memory)."""
    from igittigitt.adapters.cli.commands import _common

    giant = "x" * (_common._MAX_TOKEN_BYTES + 1024)  # no newline anywhere
    result = cli_runner.invoke(cli, ["filter", "-C", str(tmp_path)], input=giant, obj=production_factory)
    assert result.exit_code != 0
    assert "missing separator" in result.output
