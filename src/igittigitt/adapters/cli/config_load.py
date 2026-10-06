"""Load the layered configuration for the CLI, and refuse a command that needs a broken one.

The root group loads the configuration before any subcommand's options are parsed, so it
cannot report a failure the way the subcommand would, and it must not block a command that
never reads the configuration: ``config-deploy`` is how a broken file gets replaced, and
``info`` or ``--help`` have to keep working meanwhile. The root therefore records the
failure, and each command that reads the configuration asks for it through
:func:`require_config`.

What the command line itself gets wrong is not a configuration failure: a malformed or
conflicting ``--set`` or an invalid ``--profile`` name is a usage error (exit 2), checked BEFORE
loading so that a broken file cannot hide it from a command that does not read the
configuration.

Contents:
    * :func:`load_config` - load with profile, ``.env`` and ``--set``, or say why not.
    * :func:`start_logging` - start logging; an invalid ``[lib_log_rich]`` is a load failure.
    * :func:`require_config` - the configuration, or exit 78 naming the failure.
    * :func:`report_load_failure` - the one-line report, after the traceback on request.
    * :func:`echo_load_traceback` - the loader's traceback alone, for a caller with its own line.
"""

from __future__ import annotations

from traceback import format_exception
from typing import TYPE_CHECKING

import rich_click as click
from lib_layered_config import Config, ConfigError

from igittigitt.adapters.config.loader import validate_profile
from igittigitt.adapters.config.overrides import apply_overrides, nest_overrides
from igittigitt.adapters.logging.setup import InvalidLoggingConfigError

from .exit_codes import ExitCode

if TYPE_CHECKING:
    from igittigitt.composition import AppServices

    from .context import CLIContext

#: Every way loading a configuration can fail: a broken or invalid file (ConfigError, which
#: lib_layered_config's own validation error subclasses, and which also covers a TOML or
#: ``.env`` file that is not UTF-8) and a file the running user cannot read (OSError).
#: Anything else the loader raises is a bug and propagates as one.
_LOAD_ERRORS = (ConfigError, OSError)


def _check_command_line(profile: str | None, set_overrides: tuple[str, ...]) -> None:
    """Refuse a malformed or conflicting ``--set`` or an invalid ``--profile`` name (exit 2)."""
    try:
        if profile is not None:
            validate_profile(profile)
        nest_overrides(set_overrides)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc


def load_config(
    services: AppServices, *, profile: str | None, env_file: str | None, set_overrides: tuple[str, ...]
) -> tuple[Config, Exception | None]:
    """Load the layered configuration, or say why it could not be loaded.

    Args:
        services: The composition's services; only ``get_config`` is used.
        profile: The profile to load, or None for none.
        env_file: An explicit ``.env`` file, or None to search for one.
        set_overrides: The ``--set`` values, applied only to a configuration that loaded.

    Returns:
        The configuration and None, or an empty configuration and the exception that says
        why loading failed.

    Raises:
        click.UsageError: A ``--set`` value is malformed, two of them conflict, or the
            profile name is invalid; that is a command-line error (exit 2), not a
            configuration one, and it is raised whether or not the configuration would load.

    Example:
        >>> from igittigitt.composition import build_testing
        >>> config, error = load_config(build_testing(), profile=None, env_file=None, set_overrides=("a.b=1",))
        >>> config.get("a"), error
        ({'b': 1}, None)
    """
    _check_command_line(profile, set_overrides)
    try:
        config = services.get_config(profile=profile, dotenv_path=env_file)
    except _LOAD_ERRORS as exc:
        return Config({}, {}), exc
    return apply_overrides(config, set_overrides), None


def start_logging(
    services: AppServices, config: Config, config_error: Exception | None, *, env_file: str | None
) -> tuple[Config, Exception | None]:
    """Start logging with ``config``; a logging section it refuses is recorded like a load failure.

    An invalid ``[lib_log_rich]`` value would otherwise stop every command, ``config-deploy``
    (which replaces the file holding it) included. Logging then starts with its defaults, and
    the commands that read the configuration refuse with exit 78 naming the key.

    Args:
        services: The composition's services; only ``init_logging`` is used.
        config: The configuration :func:`load_config` returned.
        config_error: The failure :func:`load_config` returned, or None.
        env_file: The ``--env-file`` path, or None; logging reads its ``LOG_*`` lines from it.

    Returns:
        ``config`` and ``config_error`` unchanged, or an empty configuration and the logging
        failure when no earlier failure was recorded.
    """
    try:
        services.init_logging(config, dotenv_path=env_file)
    except InvalidLoggingConfigError as exc:
        services.init_logging(Config({}, {}), dotenv_path=env_file)
        return Config({}, {}), config_error or exc
    return config, config_error


def echo_load_traceback(error: Exception, *, show_traceback: bool) -> None:
    """Write the loader's chained traceback to stderr when ``--traceback`` was given.

    The failure is recorded, not raised, so the usual ``--traceback`` handling in ``main()``
    never sees it; without this the flag would show nothing about why loading failed.

    Args:
        error: The exception :func:`load_config` returned.
        show_traceback: Whether ``--traceback`` was given.
    """
    if show_traceback:
        click.echo("".join(format_exception(error)).rstrip(), err=True)


def report_load_failure(error: Exception, *, show_traceback: bool) -> None:
    """Write why the configuration did not load: one line per problem, after the traceback on request.

    Args:
        error: The exception :func:`load_config` returned.
        show_traceback: Whether ``--traceback`` was given.
    """
    echo_load_traceback(error, show_traceback=show_traceback)
    problems = error.problems if isinstance(error, InvalidLoggingConfigError) else [str(error)]
    for problem in problems:
        click.echo(f"Error: {problem}", err=True)


def require_config(ctx: click.Context, cli_ctx: CLIContext) -> Config:
    """Return the configuration the root loaded, or end the command with exit 78.

    Args:
        ctx: The running command's click context.
        cli_ctx: The state the root group stored.

    Returns:
        The loaded configuration.

    Raises:
        click.exceptions.Exit: The configuration could not be loaded; one stderr line names
            the reason, after the loader's traceback when ``--traceback`` was given.
    """
    if cli_ctx.config_error is not None:
        report_load_failure(cli_ctx.config_error, show_traceback=cli_ctx.traceback)
        ctx.exit(ExitCode.CONFIG_ERROR)
    return cli_ctx.config


__all__ = ["echo_load_traceback", "load_config", "report_load_failure", "require_config", "start_logging"]
