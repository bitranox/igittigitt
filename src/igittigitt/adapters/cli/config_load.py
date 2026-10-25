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
    * :class:`RootCommandLine` - the root's ``--profile`` and ``--set``, checked.
    * :func:`parse_profile_option` - a ``--profile`` value as a checked name (exit 2).
    * :func:`parse_command_line` - check the root's ``--profile`` and parse ``--set`` once (exit 2).
    * :func:`load_config` - load with profile, ``.env`` and ``--set``, or say why not.
    * :func:`start_logging` - start logging; an invalid ``[lib_log_rich]`` value or ``LOG_*``
      variable is a load failure.
    * :func:`require_config` - the configuration, or exit 78 naming the failure.
    * :func:`report_load_failure` - the one-line report, after the traceback on request.
    * :func:`echo_load_traceback` - the loader's traceback alone, for a caller with its own line.
"""

from __future__ import annotations

from dataclasses import dataclass
from traceback import format_exception
from typing import TYPE_CHECKING

import rich_click as click
from lib_layered_config import Config, ConfigError

from igittigitt.adapters.config.loader import ProfileName, parse_profile_name
from igittigitt.adapters.config.overrides import ConfigOverrides, apply_overrides, parse_overrides
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


@dataclass(frozen=True, slots=True)
class RootCommandLine:
    """What the root group's ``--profile`` and ``--set`` said, checked.

    Attributes:
        profile: The checked ``--profile`` name, or None when it was not given.
        overrides: The parsed ``--set`` values.
    """

    profile: ProfileName | None
    overrides: ConfigOverrides


def parse_profile_option(raw: str | None) -> ProfileName | None:
    """Turn a ``--profile`` value into a checked name; an invalid one is a usage error (exit 2).

    Args:
        raw: The option's value, or None when it was not given.

    Returns:
        The checked name, or None.

    Raises:
        click.UsageError: The name is empty, too long, a reserved name, or holds a path
            separator or a character outside the allowed set.

    Examples:
        >>> parse_profile_option("production")
        'production'
        >>> parse_profile_option(None) is None
        True
        >>> parse_profile_option("../x")
        Traceback (most recent call last):
        ...
        click.exceptions.UsageError: profile contains invalid characters: ../x
    """
    if raw is None:
        return None
    try:
        return parse_profile_name(raw)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc


def parse_command_line(profile: str | None, raw_overrides: tuple[str, ...]) -> RootCommandLine:
    """Check the root's ``--profile`` name, then parse its ``--set`` values, once.

    The profile comes first, so with both wrong the profile is the one reported. This is the
    only place the root's raw ``--profile`` and ``--set`` strings are read; everything after it
    takes the result.

    Args:
        profile: The root's ``--profile``, or None.
        raw_overrides: The root's ``--set`` strings, in command-line order.

    Returns:
        The checked profile name and the parsed, checked overrides.

    Raises:
        click.UsageError: The profile name is invalid, a ``--set`` value is malformed, or two
            of them conflict; a command-line error (exit 2), raised before anything is loaded.

    Example:
        >>> command_line = parse_command_line("production", ("a.b=1",))
        >>> command_line.profile, command_line.overrides.tree()
        ('production', {'a': {'b': 1}})
    """
    checked_profile = parse_profile_option(profile)
    try:
        overrides = parse_overrides(raw_overrides)
    except ValueError as exc:
        raise click.UsageError(str(exc)) from exc
    return RootCommandLine(profile=checked_profile, overrides=overrides)


def load_config(
    services: AppServices, *, profile: ProfileName | None, env_file: str | None, overrides: ConfigOverrides
) -> tuple[Config, Exception | None]:
    """Load the layered configuration, or say why it could not be loaded.

    Args:
        services: The composition's services; only ``get_config`` is used.
        profile: The checked profile to load (see :func:`parse_profile_option`), or None for none.
        env_file: An explicit ``.env`` file, or None to search for one.
        overrides: The parsed ``--set`` values, applied only to a configuration that loaded.

    Returns:
        The configuration and None, or an empty configuration and the exception that says
        why loading failed.

    Example:
        >>> from igittigitt.composition import build_testing
        >>> command_line = parse_command_line(None, ("a.b=1",))
        >>> config, error = load_config(
        ...     build_testing(), profile=command_line.profile, env_file=None, overrides=command_line.overrides
        ... )
        >>> config.get("a"), error
        ({'b': 1}, None)
    """
    try:
        config = services.get_config(profile=profile, dotenv_path=env_file)
    except _LOAD_ERRORS as exc:
        return Config({}, {}), exc
    return apply_overrides(config, overrides), None


def start_logging(
    services: AppServices, config: Config, config_error: Exception | None, *, env_file: str | None
) -> tuple[Config, Exception | None]:
    """Start logging with ``config``; a logging section it refuses is recorded like a load failure.

    An invalid ``[lib_log_rich]`` value or ``LOG_*`` variable would otherwise stop every
    command, ``config-deploy`` (which replaces the file holding it) included. ``init_logging``
    then starts logging with its defaults (and no ``LOG_*`` variable, if one of them is the
    refused setting) before it raises, and the commands that read the configuration refuse with
    exit 78 and the refusal: ``lib_log_rich.<key>: <reason>`` for a problem the section's type
    check finds, lib_log_rich's own message for a value only lib_log_rich refuses, whether it
    came from the section or a ``LOG_*`` variable (``lib_log_rich: Unknown log level: 'bogus'``).

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


__all__ = [
    "RootCommandLine",
    "echo_load_traceback",
    "load_config",
    "parse_command_line",
    "parse_profile_option",
    "report_load_failure",
    "require_config",
    "start_logging",
]
