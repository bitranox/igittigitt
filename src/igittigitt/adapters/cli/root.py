"""Root CLI command group and global option handling.

Defines the top-level Click command group that serves as the entry point for
all subcommands. Handles global flags like --traceback, --profile, and --set.

Contents:
    * :func:`cli` - Root command group with global options.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import rich_click as click
from lib_layered_config import Config

from igittigitt import __init__conf__
from igittigitt.adapters.config.overrides import apply_overrides

from .constants import CLICK_CONTEXT_SETTINGS
from .context import apply_traceback_preferences, store_cli_context
from .typed_click import option, version_option

if TYPE_CHECKING:
    from igittigitt.composition import AppServices


def _apply_cli_overrides(config: Config, set_overrides: tuple[str, ...]) -> Config:
    """Apply ``--set`` overrides to a Config, raising UsageError on failure.

    Args:
        config: Base configuration loaded from file/env layers.
        set_overrides: Raw ``SECTION.KEY=VALUE`` strings from the CLI.

    Returns:
        New Config with overrides applied, or original if none given.

    Raises:
        click.UsageError: If any override string is malformed or targets
            a non-dict section/intermediate.
    """
    try:
        return apply_overrides(config, set_overrides)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc


@click.group(
    help=__init__conf__.title,
    context_settings=CLICK_CONTEXT_SETTINGS,
    invoke_without_command=True,
)
@version_option(
    version=__init__conf__.version,
    prog_name=__init__conf__.shell_command,
    message=f"{__init__conf__.shell_command} version {__init__conf__.version}",
)
@option(
    "--traceback/--no-traceback",
    is_flag=True,
    default=False,
    help="Show full Python traceback on errors",
)
@option(
    "--profile",
    type=str,
    default=None,
    help="Load configuration from a named profile (e.g., 'production', 'test')",
)
@option(
    "--set",
    "set_overrides",
    multiple=True,
    default=(),
    metavar="SECTION.KEY=VALUE",
    help="Override a configuration setting (repeatable).",
)
@option(
    "--env-file",
    "env_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    default=None,
    help="Explicit .env file path (skips upward directory search).",
)
@click.pass_context
def cli(
    ctx: click.Context,
    traceback: bool,
    profile: str | None,
    set_overrides: tuple[str, ...],
    env_file: str | None,
) -> None:
    """Root command storing global flags and syncing shared traceback state.

    Loads configuration once with the profile, applies any ``--set`` overrides,
    and stores it in the Click context for all subcommands to access. Mirrors
    the traceback flag into ``lib_cli_exit_tools.config`` so downstream helpers
    observe the preference.

    Example:
        >>> from click.testing import CliRunner
        >>> from igittigitt.composition import build_production
        >>> runner = CliRunner()
        >>> result = runner.invoke(cli, ["--help"], obj=build_production)
        >>> result.exit_code
        0
    """
    # ctx.obj is always the services factory (production or test)
    if not callable(ctx.obj):
        raise RuntimeError("Services factory not provided. This is a bug.")
    services: AppServices = ctx.obj()  # type: ignore[assignment]  # Click's obj is typed as Any
    config = services.get_config(profile=profile, dotenv_path=env_file)
    config = _apply_cli_overrides(config, set_overrides)
    services.init_logging(config)
    store_cli_context(
        ctx,
        traceback=traceback,
        config=config,
        services=services,
        profile=profile,
        set_overrides=set_overrides,
    )
    apply_traceback_preferences(traceback)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Deferred import required to break a circular dependency: this module defines
# the ``cli`` group, commands register themselves onto it, and those command
# modules import from package ancestors. This is the standard Click pattern.
def _register_commands() -> None:
    from .commands import (
        cli_check,
        cli_config,
        cli_config_deploy,
        cli_config_generate_examples,
        cli_filter,
        cli_info,
        cli_logdemo,
    )

    for cmd in (
        cli_info,
        cli_check,
        cli_filter,
        cli_config,
        cli_config_deploy,
        cli_config_generate_examples,
        cli_logdemo,
    ):
        cli.add_command(cmd)


_register_commands()


__all__ = ["cli"]
