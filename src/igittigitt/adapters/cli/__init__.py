"""CLI package - public facade for the command-line interface."""

from __future__ import annotations

from .commands import (
    cli_check,
    cli_config,
    cli_config_deploy,
    cli_config_generate_examples,
    cli_filter,
    cli_info,
    cli_logdemo,
)
from .constants import CLICK_CONTEXT_SETTINGS, TRACEBACK_SUMMARY_LIMIT, TRACEBACK_VERBOSE_LIMIT
from .context import (
    CLIContext,
    TracebackState,
    apply_traceback_preferences,
    get_cli_context,
    restore_traceback_state,
    snapshot_traceback_state,
    store_cli_context,
)
from .exit_codes import ExitCode
from .main import main
from .root import cli

__all__ = [
    # Constants
    "CLICK_CONTEXT_SETTINGS",
    "TRACEBACK_SUMMARY_LIMIT",
    "TRACEBACK_VERBOSE_LIMIT",
    # Exit codes
    "ExitCode",
    # Context + traceback management
    "CLIContext",
    "TracebackState",
    "apply_traceback_preferences",
    "get_cli_context",
    "restore_traceback_state",
    "snapshot_traceback_state",
    "store_cli_context",
    # Root command + entry
    "cli",
    "main",
    # Commands
    "cli_check",
    "cli_config",
    "cli_config_deploy",
    "cli_config_generate_examples",
    "cli_filter",
    "cli_info",
    "cli_logdemo",
]
