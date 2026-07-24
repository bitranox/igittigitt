"""Shared pytest fixtures and coverage-database setup."""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import lib_cli_exit_tools
import pytest
from click.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_COVERAGE_BASENAME = ".coverage.igittigitt"


def _purge_stale_coverage_files(cov_path: Path) -> None:
    """Delete leftover SQLite sidecar files from crashed runs (avoids 'database is locked')."""
    for suffix in ("", "-journal", "-wal", "-shm"):
        with contextlib.suppress(FileNotFoundError):
            Path(str(cov_path) + suffix).unlink()


def pytest_configure(config: pytest.Config) -> None:
    """Redirect the coverage database to a local temp dir (network-mount SQLite locking)."""
    if "COVERAGE_FILE" not in os.environ:
        cov_path = Path(tempfile.gettempdir()) / _COVERAGE_BASENAME
        _purge_stale_coverage_files(cov_path)
        os.environ["COVERAGE_FILE"] = str(cov_path)


ANSI_ESCAPE_PATTERN = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a fresh Click CliRunner per test."""
    return CliRunner()


@pytest.fixture
def production_factory() -> Callable[[], object]:
    """The production services factory, passed to the CLI via ``obj=``."""
    from igittigitt.composition import build_production

    return build_production


@pytest.fixture
def strip_ansi() -> Callable[[str], str]:
    """Return a helper that strips ANSI escape sequences from a string."""

    def _strip(value: str) -> str:
        return ANSI_ESCAPE_PATTERN.sub("", value)

    return _strip


@pytest.fixture
def managed_traceback_state() -> Iterator[None]:
    """Reset traceback flags to a known baseline and restore them afterwards."""
    lib_cli_exit_tools.reset_config()
    lib_cli_exit_tools.config.traceback = False
    lib_cli_exit_tools.config.traceback_force_color = False
    try:
        yield
    finally:
        lib_cli_exit_tools.reset_config()
        lib_cli_exit_tools.config.traceback = False
        lib_cli_exit_tools.config.traceback_force_color = False
