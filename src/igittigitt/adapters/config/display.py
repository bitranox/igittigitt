"""Display configuration - delegates to lib_layered_config.

Thin wrapper around lib_layered_config's Rich-styled display_config,
adding log flush before output to prevent mixing log messages with
configuration display.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import lib_log_rich.runtime
from lib_layered_config import Config
from lib_layered_config import OutputFormat as LibOutputFormat
from lib_layered_config import display_config as _lib_display

from igittigitt.domain.enums import OutputFormat

if TYPE_CHECKING:
    from rich.console import Console


def display_config(
    config: Config,
    *,
    output_format: OutputFormat = OutputFormat.HUMAN,
    section: str | None = None,
    console: Console | None = None,
    profile: str | None = None,
) -> None:
    """Display configuration using lib_layered_config's Rich display.

    Flushes any pending log output before displaying to prevent
    mixing log messages with configuration output.

    Args:
        config: Already-loaded layered configuration object to display.
        output_format: Output format: OutputFormat.HUMAN for TOML-like display or
            OutputFormat.JSON for JSON. Defaults to OutputFormat.HUMAN.
        section: Optional section name to display only that section. When None,
            displays all configuration.
        console: Optional Rich Console for output. When None, uses the module-level
            default. Primarily useful for testing.
        profile: Optional profile name to include in provenance comments.

    Side Effects:
        Flushes pending log messages before display.
        Writes formatted configuration to stdout.

    Raises:
        ValueError: If a section was requested that doesn't exist.
    """
    if lib_log_rich.runtime.is_initialised():
        lib_log_rich.runtime.flush()

    lib_format = LibOutputFormat(output_format.value)
    _lib_display(config, output_format=lib_format, section=section, profile=profile, console=console)


__all__ = ["display_config"]
