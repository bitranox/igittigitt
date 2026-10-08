"""Exit codes and stderr through the real ``main()`` entry point.

``CliRunner.invoke(cli, ...)`` calls the click command tree directly and never runs
``main()``'s ``standalone_mode=False`` handling, which is where a command's exit code reaches
the process. These tests go through ``main()`` itself, as a console script does, with the
services replaced at the composition seam.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

import pytest
import rich_click as click

from igittigitt.adapters.cli import cli
from igittigitt.adapters.cli.main import main
from igittigitt.composition import AppServices, build_testing

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


def _services(**overrides: Any) -> Callable[[], AppServices]:
    def build() -> AppServices:
        return dataclasses.replace(build_testing(), **overrides)

    return build


def _raising(error: Exception) -> Callable[..., Any]:
    def raise_it(*_args: Any, **_kwargs: Any) -> Any:
        raise error

    return raise_it


@click.command("exit-through-context")
@click.pass_context
def _exit_through_context(ctx: click.Context) -> None:
    """Leave through ``ctx.exit``, the way click itself ends a command early."""
    ctx.exit(3)


@pytest.fixture
def command_exiting_through_context() -> Iterator[str]:
    """Register a throwaway command that exits 3 through click's context, then remove it."""
    name = "exit-through-context"
    cli.add_command(_exit_through_context, name)
    try:
        yield name
    finally:
        cli.commands.pop(name, None)


@pytest.mark.os_agnostic
def test_an_exit_through_the_click_context_keeps_its_code(command_exiting_through_context: str) -> None:
    """rich_click's ``main()`` RETURNS the code of a ``ctx.exit`` under ``standalone_mode=False``;
    ``main()`` must pass it on instead of discarding it and reporting success."""
    exit_code = main([command_exiting_through_context], services_factory=build_testing)

    assert exit_code == 3


@pytest.mark.os_agnostic
def test_a_command_that_returns_normally_exits_0() -> None:
    assert main(["info"], services_factory=build_testing) == 0


@pytest.mark.os_agnostic
def test_a_refused_deploy_exits_13_without_printing_systemexit(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        ["config-deploy", "--target", "user"],
        services_factory=_services(deploy_configuration=_raising(PermissionError("read-only"))),
    )

    err = capsys.readouterr().err
    assert exit_code == 13
    assert "Permission denied" in err
    assert "SystemExit" not in err
