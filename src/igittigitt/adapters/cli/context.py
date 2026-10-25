"""Click context helpers for CLI state management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import lib_cli_exit_tools

from igittigitt.adapters.config.overrides import NO_OVERRIDES, ConfigOverrides

if TYPE_CHECKING:
    import rich_click as click
    from lib_layered_config import Config

    from igittigitt.adapters.config.loader import ProfileName
    from igittigitt.composition import AppServices


@dataclass(frozen=True, slots=True)
class TracebackState:
    """Captured traceback configuration of ``lib_cli_exit_tools.config``.

    Attributes:
        traceback: Whether full tracebacks are printed.
        force_color: Whether tracebacks are coloured even off a terminal.
    """

    traceback: bool
    force_color: bool


@dataclass(slots=True)
class CLIContext:
    """Typed CLI context for Click subcommand access.

    Attributes:
        traceback: Whether verbose tracebacks were requested.
        config: The loaded layered configuration; empty when ``config_error`` is set, so a
            command that reads it asks through ``config_load.require_config``.
        services: All application services from the composition layer.
        profile: The root's checked ``--profile`` name, or None.
        set_overrides: The root's parsed ``--set`` values, reapplied when a subcommand
            reloads the configuration with another profile.
        env_file: The root's ``--env-file``, for the same reload.
        config_error: Why the configuration could not be loaded, None when it loaded. The
            root records the exception; each command that reads the configuration reports it.
    """

    traceback: bool
    config: Config
    services: AppServices
    profile: ProfileName | None = None
    set_overrides: ConfigOverrides = NO_OVERRIDES
    env_file: str | None = None
    config_error: Exception | None = None


def store_cli_context(
    ctx: click.Context,
    *,
    traceback: bool,
    config: Config,
    services: AppServices,
    profile: ProfileName | None = None,
    set_overrides: ConfigOverrides = NO_OVERRIDES,
    env_file: str | None = None,
    config_error: Exception | None = None,
) -> None:
    """Store CLI state in the Click context for subcommand access.

    Args:
        ctx: Click context associated with the current invocation.
        traceback: Whether verbose tracebacks were requested.
        config: Loaded layered configuration object for all subcommands.
        services: All application services from composition layer.
        profile: The root's checked ``--profile`` name, or None.
        set_overrides: The root's parsed ``--set`` values, for reapplication when a
            subcommand reloads config with a different profile.
        env_file: The root's ``--env-file``, for the same reload.
        config_error: Why the configuration could not be loaded, None when it loaded.

    Example:
        >>> from click.testing import CliRunner
        >>> from unittest.mock import MagicMock
        >>> from igittigitt.adapters.config.loader import parse_profile_name
        >>> from igittigitt.composition import build_production
        >>> ctx = MagicMock()
        >>> ctx.obj = None
        >>> mock_config = MagicMock()
        >>> services = build_production()
        >>> profile = parse_profile_name("test")
        >>> store_cli_context(ctx, traceback=True, config=mock_config, services=services, profile=profile)
        >>> ctx.obj.traceback
        True
    """
    ctx.obj = CLIContext(
        traceback=traceback,
        config=config,
        services=services,
        profile=profile,
        set_overrides=set_overrides,
        env_file=env_file,
        config_error=config_error,
    )


def get_cli_context(ctx: click.Context) -> CLIContext:
    """Retrieve typed CLI state from Click context.

    Args:
        ctx: Click context containing CLI state.

    Returns:
        CLIContext dataclass with typed access to CLI state.

    Raises:
        RuntimeError: If CLI context was not properly initialized.

    Example:
        >>> from unittest.mock import MagicMock
        >>> ctx = MagicMock()
        >>> mock_config = MagicMock()
        >>> mock_services = MagicMock()
        >>> ctx.obj = CLIContext(traceback=False, config=mock_config, services=mock_services)
        >>> cli_ctx = get_cli_context(ctx)
        >>> cli_ctx.traceback
        False
    """
    if not isinstance(ctx.obj, CLIContext):
        raise RuntimeError("CLI context not initialized. Call store_cli_context first.")
    return ctx.obj


def apply_traceback_preferences(enabled: bool) -> None:
    """Synchronise shared traceback flags with the requested preference.

    Args:
        enabled: ``True`` enables full tracebacks with colour.

    Example:
        >>> apply_traceback_preferences(True)
        >>> bool(lib_cli_exit_tools.config.traceback)
        True
    """
    lib_cli_exit_tools.config.traceback = bool(enabled)
    lib_cli_exit_tools.config.traceback_force_color = bool(enabled)


def snapshot_traceback_state() -> TracebackState:
    """Capture the current traceback configuration for later restoration.

    Returns:
        The current traceback and force-colour flags.

    Example:
        >>> apply_traceback_preferences(False)
        >>> snapshot_traceback_state()
        TracebackState(traceback=False, force_color=False)
    """
    return TracebackState(
        traceback=bool(getattr(lib_cli_exit_tools.config, "traceback", False)),
        force_color=bool(getattr(lib_cli_exit_tools.config, "traceback_force_color", False)),
    )


def restore_traceback_state(state: TracebackState) -> None:
    """Reapply a previously captured traceback configuration.

    Args:
        state: A state from :func:`snapshot_traceback_state`.

    Example:
        >>> original = snapshot_traceback_state()
        >>> apply_traceback_preferences(True)
        >>> restore_traceback_state(original)
        >>> snapshot_traceback_state() == original
        True
    """
    lib_cli_exit_tools.config.traceback = state.traceback
    lib_cli_exit_tools.config.traceback_force_color = state.force_color


__all__ = [
    "CLIContext",
    "TracebackState",
    "apply_traceback_preferences",
    "get_cli_context",
    "restore_traceback_state",
    "snapshot_traceback_state",
    "store_cli_context",
]
