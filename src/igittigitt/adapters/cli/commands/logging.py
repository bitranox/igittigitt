"""Logging demonstration CLI command.

Provides a command to preview log output using lib_log_rich's logdemo facility.

Contents:
    * :func:`cli_logdemo` - Run a logging demonstration.
"""

from __future__ import annotations

import lib_log_rich
import lib_log_rich.runtime
import rich_click as click
from lib_log_rich.domain import ConsoleTheme

from ..constants import CLICK_CONTEXT_SETTINGS
from ..typed_click import option


@click.command("logdemo", context_settings=CLICK_CONTEXT_SETTINGS)
@option(
    "--theme",
    # The library's own theme list, so an unknown name is a usage error (exit 2) rather than the
    # ValueError logdemo() raises, which main() would turn into an OS-specific errno.
    type=click.Choice([member.value for member in ConsoleTheme], case_sensitive=False),
    default=ConsoleTheme.CLASSIC.value,
    help="Logging theme to preview",
)
@click.pass_context
def cli_logdemo(ctx: click.Context, theme: str) -> None:
    """Run a logging demonstration to preview log output."""
    # logdemo() requires uninitialized runtime
    if lib_log_rich.runtime.is_initialised():
        lib_log_rich.runtime.shutdown()

    result = lib_log_rich.logdemo(theme=ConsoleTheme(theme.lower()))
    click.echo(f"\nLog demo completed (theme: {result.theme})")


__all__ = ["cli_logdemo"]
