"""Integration tests for our USAGE of the external config/logging libraries.

We do not re-test lib_layered_config / lib_log_rich internals (those are external
and tested upstream). We test that our adapters wire and drive them correctly:
config-deploy writes the expected files, `config` renders the merged settings, the
in-memory test adapters work, and the CLI error boundary turns an unexpected
exception into a clean, formatted exit - the integration points we actually own.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner

from igittigitt import __init__conf__
from igittigitt.adapters.cli import cli, main
from igittigitt.composition import build_production, build_testing

Factory = Callable[[], object]


# --- config adapters: our usage of lib_layered_config -------------------------


@pytest.mark.os_agnostic
def test_config_deploy_writes_files(
    cli_runner: CliRunner, production_factory: Factory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`config-deploy --target user` actually writes the bundled config files."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    result = cli_runner.invoke(cli, ["config-deploy", "--target", "user"], obj=production_factory)
    assert result.exit_code == 0, result.output
    deployed = {p.name for p in tmp_path.rglob("*.toml")}
    assert "50-performance.toml" in deployed
    assert "90-logging.toml" in deployed


@pytest.mark.os_agnostic
def test_config_renders_merged_settings(cli_runner: CliRunner, production_factory: Factory) -> None:
    """`config` displays the merged configuration, including a known knob."""
    result = cli_runner.invoke(cli, ["config"], obj=production_factory)
    assert result.exit_code == 0
    assert "dir_cache_max" in result.output


@pytest.mark.os_agnostic
def test_config_generate_examples_writes(cli_runner: CliRunner, production_factory: Factory, tmp_path: Path) -> None:
    result = cli_runner.invoke(
        cli, ["config-generate-examples", "--destination", str(tmp_path)], obj=production_factory
    )
    assert result.exit_code == 0
    assert list(tmp_path.rglob("*")), "expected example files to be written"


@pytest.mark.os_agnostic
def test_in_memory_services_are_usable() -> None:
    """The in-memory test adapters (build_testing) wire and run without I/O."""
    services = build_testing()
    config = services.get_config()
    services.init_logging(config)  # no-op logging adapter
    services.display_config(config)  # in-memory display
    assert services.get_default_config_path() is not None


# --- CLI error boundary: our usage of lib_cli_exit_tools ----------------------


@pytest.mark.os_agnostic
def test_error_boundary_formats_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], managed_traceback_state: None
) -> None:
    """An unexpected exception is formatted to a non-zero exit, no traceback by default."""

    def boom() -> None:
        raise RuntimeError("kaboom-xyz")

    monkeypatch.setattr(__init__conf__, "print_info", boom)
    code = main(["info"], services_factory=build_production)
    err = capsys.readouterr().err
    assert code != 0
    assert "kaboom-xyz" in err or "RuntimeError" in err
    assert "Traceback (most recent call last)" not in err


@pytest.mark.os_agnostic
def test_error_boundary_traceback_flag_shows_full_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    managed_traceback_state: None,
    strip_ansi: Callable[[str], str],
) -> None:
    """--traceback turns the boundary's summary into a full traceback."""

    def boom() -> None:
        raise RuntimeError("kaboom-tb")

    monkeypatch.setattr(__init__conf__, "print_info", boom)
    code = main(["--traceback", "info"], services_factory=build_production)
    err = strip_ansi(capsys.readouterr().err)
    assert code != 0
    assert "Traceback (most recent call last)" in err
    assert "RuntimeError" in err
