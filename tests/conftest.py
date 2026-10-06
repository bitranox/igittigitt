"""Shared pytest fixtures and coverage-database setup."""

from __future__ import annotations

import contextlib
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import lib_cli_exit_tools
import lib_log_rich.runtime
import pytest
import rich_click.rich_click
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


def _restore_logging_state(handlers: list[logging.Handler], level: int, propagate: bool) -> None:
    """Shut down a live lib_log_rich runtime and put the root logger back as it was.

    ``runtime.shutdown()`` alone is not enough: production ``init_logging`` also attaches a
    stdlib handler to the root logger and raises its level, and shutting the runtime down
    undoes neither, so a later test's stdlib warnings would be swallowed.
    """
    if lib_log_rich.runtime.is_initialised():
        lib_log_rich.runtime.shutdown()
    root = logging.getLogger()
    root.handlers[:] = handlers
    root.setLevel(level)
    root.propagate = propagate


@pytest.fixture(autouse=True)
def isolated_logging_state() -> Iterator[Callable[[], None]]:
    """Reset the process-global logging state after every test.

    The lib_log_rich runtime and the stdlib root logger are process-global. Once a command
    (under the production or the testing composition) starts a runtime, it would otherwise
    stay live for every later test, so a test would pass or fail by what ran before it rather
    than by its own setup. The root logger is snapshotted before the test and restored after,
    together with shutting the runtime down.

    Yields:
        The same restore step, so a test can apply it mid-test and assert its effect.
    """
    root = logging.getLogger()
    handlers, level, propagate = list(root.handlers), root.level, root.propagate

    def _restore() -> None:
        _restore_logging_state(handlers, level, propagate)

    yield _restore
    _restore()


#: The width every test's CLI output is rendered at. Wider than the 80 columns the assertions were
#: written against, so a message that fits one line there cannot wrap on a narrower runner.
_CLI_OUTPUT_WIDTH = 120


@pytest.fixture(autouse=True)
def deterministic_cli_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every test the same uncoloured, fixed-width CLI output, on any machine and in CI.

    rich-click decides colour and width once, when it is imported, into module globals that each
    command reads again when it formats an error; an environment variable changed per test arrives
    after that import and changes nothing, so the globals are reset here:

    - ``FORCE_TERMINAL`` comes from FORCE_COLOR, PY_COLORS or GITHUB_ACTIONS, and GitHub sets
      GITHUB_ACTIONS on every runner, so CI output was coloured and local output was not.
    - ``WIDTH`` and ``MAX_WIDTH`` come from the terminal, which is 79 columns on the Windows
      runners and 80 elsewhere, so an error box wraps its message on a narrow terminal.

    rich itself reads FORCE_COLOR whenever a ``Console`` is built, which happens per command, so
    removing the variable for the test reaches it. A console built at import time is out of reach
    of all of this: lib_layered_config's default display console is one, so a ``display_config``
    test still sees colour when FORCE_COLOR is exported for the whole run.
    """
    monkeypatch.setattr(rich_click.rich_click, "FORCE_TERMINAL", None)
    monkeypatch.setattr(rich_click.rich_click, "WIDTH", _CLI_OUTPUT_WIDTH)
    monkeypatch.setattr(rich_click.rich_click, "MAX_WIDTH", _CLI_OUTPUT_WIDTH)
    monkeypatch.delenv("FORCE_COLOR", raising=False)


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
