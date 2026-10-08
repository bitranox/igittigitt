"""The testing composition's logging runtime, and the per-test reset of logging state.

Every command binds job context onto the process-global lib_log_rich runtime, so the
in-memory logging adapter must leave a live runtime behind or ``build_testing()`` cannot run
a single command. That runtime (and the root logger that production ``init_logging``
mutates) is process-global, so the suite restores both after every test; the
``isolated_logging_state`` fixture hands a test the same restore step so it can prove the
reset within one test instead of relying on test order.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import lib_log_rich.runtime
import pytest
from lib_layered_config import Config

from igittigitt.adapters.cli import cli
from igittigitt.adapters.logging.setup import init_logging
from igittigitt.composition import build_testing

if TYPE_CHECKING:
    from collections.abc import Callable

    from click.testing import CliRunner


@pytest.mark.os_agnostic
@pytest.mark.parametrize("command", ["info", "config"])
def test_a_command_that_binds_runs_under_build_testing(cli_runner: CliRunner, command: str) -> None:
    """Each of these calls ``lib_log_rich.runtime.bind(...)``, which raises unless a runtime is live."""
    result = cli_runner.invoke(cli, [command], obj=build_testing)

    assert result.exception is None, result.exception
    assert result.exit_code == 0, result.output


@pytest.mark.os_agnostic
def test_the_reset_shuts_down_the_runtime_a_command_started(
    cli_runner: CliRunner, isolated_logging_state: Callable[[], None]
) -> None:
    result = cli_runner.invoke(cli, ["info"], obj=build_testing)
    assert result.exit_code == 0, result.output
    assert lib_log_rich.runtime.is_initialised() is True

    isolated_logging_state()

    assert lib_log_rich.runtime.is_initialised() is False


@pytest.mark.os_agnostic
def test_the_reset_restores_the_root_logger_a_production_init_changed(
    isolated_logging_state: Callable[[], None],
) -> None:
    """Production ``init_logging`` attaches a stdlib handler to the root logger and raises its
    level; ``runtime.shutdown()`` undoes neither, so the reset must, or a later test's stdlib
    warnings are swallowed depending on which test ran first."""
    root = logging.getLogger()
    before = (list(root.handlers), root.level, root.propagate)

    init_logging(Config({}, {}))
    assert (list(root.handlers), root.level, root.propagate) != before

    isolated_logging_state()

    assert (list(root.handlers), root.level, root.propagate) == before
