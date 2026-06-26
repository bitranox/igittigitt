"""Strictly-typed wrappers for the rich_click decorators with unknown types.

rich_click ships ``py.typed``, but it re-exports click's ``option`` and
``version_option`` decorators, whose ``type: ParamType[Unknown]`` parameter makes
pyright (strict mode) report ``reportUnknownMemberType`` at every call site.
Wrapping the two affected decorators here behind explicit, fully-known
signatures keeps the rest of the CLI layer strict-clean without disabling the
rule. This module is the single boundary that touches the untyped surface, so
the only ``# pyright: ignore`` for this third-party gap lives here.

Other click members (``command``, ``group``, ``echo``, ``Context``, ``Path`` …)
type cleanly and are still used directly as ``click.X`` at call sites.
"""

from collections.abc import Callable
from typing import Any

import rich_click as click

# Click decorators turn a command function (or another decorator's result) into
# a wrapped callable. ``Any`` is fully known to pyright (unlike ``Unknown``), so
# this alias is strict-clean and works both as ``@option(...)`` and as a value
# collected into a list (see email/_common.py's shared-options pattern).
_CommandDecorator = Callable[[Callable[..., Any]], Callable[..., Any]]


def option(*param_decls: str, **attrs: Any) -> _CommandDecorator:
    """Typed wrapper over :func:`rich_click.option`. See module docstring."""
    return click.option(*param_decls, **attrs)  # pyright: ignore[reportUnknownMemberType]


def version_option(*param_decls: str, **attrs: Any) -> _CommandDecorator:
    """Typed wrapper over :func:`rich_click.version_option`. See module docstring."""
    return click.version_option(*param_decls, **attrs)  # pyright: ignore[reportUnknownMemberType]


__all__ = ["option", "version_option"]
