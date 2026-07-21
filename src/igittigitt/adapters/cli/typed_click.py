"""Strictly-typed wrappers for rich_click's partially-typed decorators.

rich_click ships ``py.typed``, but its ``option````, ``argument`` and ``version_option``
decorators are typed with a partially-unknown return, so the strict type checker
reports ``reportUnknownMemberType`` at every call site. click's own decorators
are fully typed, but they default the parameter class to ``click.Option`` rather
than rich_click's ``RichOption``, which would change help rendering.

This module forwards to rich_click's decorators (so ``RichOption``/``RichArgument``
are still used at runtime) through a typed ``Protocol``: the ``cast`` is a no-op
at runtime, and the wrappers keep the exact same public signatures they always
had, so no rule needs to be silenced anywhere.

Other click members (``command``, ``group``, ``echo``, ``Context``, ``Path`` ...)
type cleanly and are still used directly as ``click.X`` at call sites.
"""

from collections.abc import Callable
from typing import Any, Protocol, cast

import rich_click as click

# Click decorators turn a command function (or another decorator's result) into a
# wrapped callable. ``Any`` is fully known to the type checker, so this alias stays
# clean and works both as ``@option(...)`` and as a value collected into a list.
_CommandDecorator = Callable[[Callable[..., Any]], Callable[..., Any]]


class _RichClickDecorators(Protocol):
    """rich_click's decorator surface, declared with complete types."""

    argument: Callable[..., _CommandDecorator]
    option: Callable[..., _CommandDecorator]
    version_option: Callable[..., _CommandDecorator]


# ``cast`` is type-only; at runtime these forward to rich_click's own decorators,
# so ``RichOption``/``RichArgument`` behavior is unchanged.
_click = cast("_RichClickDecorators", click)


def option(*param_decls: str, **attrs: Any) -> _CommandDecorator:
    """Typed wrapper over :func:`rich_click.option`. See module docstring."""
    return _click.option(*param_decls, **attrs)


def argument(*param_decls: str, **attrs: Any) -> _CommandDecorator:
    """Typed wrapper over :func:`rich_click.argument`. See module docstring."""
    return _click.argument(*param_decls, **attrs)


def version_option(*param_decls: str, **attrs: Any) -> _CommandDecorator:
    """Typed wrapper over :func:`rich_click.version_option`. See module docstring."""
    return _click.version_option(*param_decls, **attrs)


__all__ = ["argument", "option", "version_option"]
