"""Click context helpers for CLI state management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import lib_cli_exit_tools

if TYPE_CHECKING:
    import rich_click as click
    from lib_layered_config import Config

    from igittigitt.composition import AppServices

TracebackState = tuple[bool, bool]
"""Captured traceback configuration: (traceback_enabled, force_color)."""


@dataclass(slots=True)
class CLIContext:
    """Typed CLI context for Click subcommand access."""

    traceback: bool
    config: Config
    services: AppServices
    profile: str | None = None
    set_overrides: tuple[str, ...] = ()


def store_cli_context(
    ctx: click.Context,
    *,
    traceback: bool,
    config: Config,
    services: AppServices,
    profile: str | None = None,
    set_overrides: tuple[str, ...] = (),
) -> None:
    """Store CLI state in the Click context for subcommand access.

    Args:
        ctx: Click context associated with the current invocation.
        traceback: Whether verbose tracebacks were requested.
        config: Loaded layered configuration object for all subcommands.
        services: All application services from composition layer.
        profile: Optional configuration profile name.
        set_overrides: Raw ``--set`` override strings for reapplication when
            subcommands reload config with a different profile.

    Example:
        >>> from click.testing import CliRunner
        >>> from unittest.mock import MagicMock
        >>> from igittigitt.composition import build_production
        >>> ctx = MagicMock()
        >>> ctx.obj = None
        >>> mock_config = MagicMock()
        >>> services = build_production()
        >>> store_cli_context(ctx, traceback=True, config=mock_config, services=services, profile="test")
        >>> ctx.obj.traceback
        True
    """
    ctx.obj = CLIContext(
        traceback=traceback,
        config=config,
        services=services,
        profile=profile,
        set_overrides=set_overrides,
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
        Tuple of (traceback_enabled, force_color) booleans.

    Example:
        >>> state = snapshot_traceback_state()
        >>> isinstance(state, tuple) and len(state) == 2
        True
    """
    return (
        bool(getattr(lib_cli_exit_tools.config, "traceback", False)),
        bool(getattr(lib_cli_exit_tools.config, "traceback_force_color", False)),
    )


def restore_traceback_state(state: TracebackState) -> None:
    """Reapply a previously captured traceback configuration.

    Args:
        state: Tuple from :func:`snapshot_traceback_state`.

    Example:
        >>> original = snapshot_traceback_state()
        >>> apply_traceback_preferences(True)
        >>> restore_traceback_state(original)
        >>> lib_cli_exit_tools.config.traceback == original[0]
        True
    """
    lib_cli_exit_tools.config.traceback = state[0]
    lib_cli_exit_tools.config.traceback_force_color = state[1]


__all__ = [
    "CLIContext",
    "TracebackState",
    "apply_traceback_preferences",
    "get_cli_context",
    "restore_traceback_state",
    "snapshot_traceback_state",
    "store_cli_context",
]
