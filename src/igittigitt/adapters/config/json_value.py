"""Read one JSON value with orjson where it can run, and stdlib json with the same answers elsewhere.

orjson ships no free-threaded build, and importing a build without free-threading support turns the
GIL back on; from Python 3.14 it is only an optional extra. So a free-threaded interpreter, or one
without orjson installed, reads with the standard library, which here answers as orjson does on
every input where the two differ by default (measured against orjson 3.13):

- ``NaN``, ``Infinity`` and ``-Infinity`` are refused, anywhere in the value.
- A number too large to be finite (``1e400``) is refused.
- Text holding a lone surrogate escape (``"\\ud800"``) is refused.
- An integer outside ``-2**63 .. 2**64-1`` is read as a float.
- A value nesting deeper than 1024 levels is refused.

One difference remains: on Python 3.10 and 3.11 the stdlib parser stops at Python's recursion
limit, about 1000 levels, so it refuses some values orjson reads. orjson is a required dependency
there, so the stdlib reader runs on them only when orjson is missing.

Contents:
    * :class:`JsonValueError` - a refused value.
    * :func:`read_json_value` - read one value with the reader this interpreter uses.
    * :func:`read_with_stdlib` - the stdlib reader, also used directly by the parity tests.
    * :func:`select_reader` - choose the reader.
"""

from __future__ import annotations

import importlib
import json
import math
import sysconfig
from typing import TYPE_CHECKING, Final, Protocol, cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

__all__ = ["JsonValueError", "read_json_value", "read_with_stdlib", "select_reader"]

#: The integer range orjson reads as an int; outside it orjson reads a float.
_INT_MIN: Final[int] = -(2**63)
_INT_MAX: Final[int] = 2**64 - 1

#: Integer text longer than this is outside the range anyway; keeping it away from int() keeps it
#: away from Python's 4300-digit conversion limit.
_MAX_INT_TEXT: Final[int] = 20

#: orjson refuses a value nesting deeper than this.
_MAX_DEPTH: Final[int] = 1024


class JsonValueError(ValueError):
    """The text is not a JSON value orjson would accept."""


class _OrjsonModule(Protocol):
    """The part of the ``orjson`` module the reader uses."""

    def loads(self, obj: str, /) -> object: ...


def read_with_stdlib(text: str) -> object:
    """Read *text* with stdlib json, refusing and converting exactly where orjson does.

    Raises:
        JsonValueError: For text orjson would refuse.

    Examples:
        >>> read_with_stdlib('{"a": [1, true, null]}')
        {'a': [1, True, None]}
        >>> read_with_stdlib("18446744073709551616")
        1.8446744073709552e+19
        >>> read_with_stdlib("NaN")
        Traceback (most recent call last):
        ...
        igittigitt.adapters.config.json_value.JsonValueError: NaN is not a JSON value
    """
    try:
        value: object = json.loads(
            text, parse_int=_orjson_int, parse_float=_finite_float, parse_constant=_refuse_constant
        )
    except RecursionError as error:
        # Python 3.10/3.11 stop at the recursion limit, below orjson's depth limit; orjson is a
        # required dependency there, so this reader only meets it when someone calls it directly.
        raise JsonValueError("the value nests too deep") from error
    except ValueError as error:  # json.JSONDecodeError and the refusals of the hooks below
        raise JsonValueError(str(error)) from error
    _refuse_orjson_only(value)
    return value


def _orjson_int(text: str) -> int | float:
    """Read an integer literal as orjson does: an int inside the 64-bit range, else a float.

    Examples:
        >>> _orjson_int("18446744073709551615"), _orjson_int("-9223372036854775809")
        (18446744073709551615, -9.223372036854776e+18)
    """
    if len(text) > _MAX_INT_TEXT:
        return _finite_float(text)
    number = int(text)
    return number if _INT_MIN <= number <= _INT_MAX else float(text)


def _finite_float(text: str) -> float:
    """Read a number literal as a float, refusing one too large to be finite, as orjson does."""
    number = float(text)
    if not math.isfinite(number):
        raise ValueError(f"number is infinity when parsed as double: {text[:32]}")
    return number


def _refuse_constant(name: str) -> object:
    """Refuse ``NaN``, ``Infinity`` and ``-Infinity``, which are not JSON and which orjson refuses."""
    raise ValueError(f"{name} is not a JSON value")


def _refuse_orjson_only(value: object) -> None:
    """Refuse a parsed value nesting deeper than orjson allows, or holding a lone surrogate.

    Walks with an explicit stack, since the value may nest past Python's recursion limit.

    Raises:
        JsonValueError: For either reason.
    """
    pending: list[tuple[object, int]] = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        if isinstance(node, str):
            _refuse_lone_surrogate(node)
            continue
        if not isinstance(node, (dict, list)):
            continue
        if depth + 1 > _MAX_DEPTH:
            raise JsonValueError(f"the value nests deeper than {_MAX_DEPTH} levels")
        if isinstance(node, dict):
            mapping = cast("dict[str, object]", node)
            pending.extend((key, depth + 1) for key in mapping)
            pending.extend((item, depth + 1) for item in mapping.values())
        else:
            pending.extend((item, depth + 1) for item in cast("list[object]", node))


def _refuse_lone_surrogate(text: str) -> None:
    """Refuse text holding an unpaired surrogate, which no UTF-8 text can carry."""
    if text.isascii():
        return
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise JsonValueError("the value holds a lone surrogate escape") from error


def _import_orjson() -> ModuleType | None:
    # By name, not an import statement: orjson is not installed on Python 3.14+ unless the
    # "orjson" extra asks for it, and a static import would leave the type checker unable to
    # resolve the module there.
    try:
        return importlib.import_module("orjson")
    except ImportError:
        return None


def select_reader(*, free_threaded: bool, import_orjson: Callable[[], ModuleType | None]) -> Callable[[str], object]:
    """Return orjson's reader when it can run here, else :func:`read_with_stdlib`.

    Args:
        free_threaded: Whether the interpreter is a free-threaded build. orjson is never imported
            there: it has no free-threaded build, and importing one would turn the GIL back on.
        import_orjson: Returns the ``orjson`` module, or ``None`` when it is not installed.

    Examples:
        >>> select_reader(free_threaded=True, import_orjson=lambda: None) is read_with_stdlib
        True
    """
    if free_threaded:
        return read_with_stdlib
    orjson = import_orjson()
    if orjson is None:
        return read_with_stdlib
    module = cast("_OrjsonModule", orjson)

    def read_with_orjson(text: str) -> object:
        try:
            return module.loads(text)
        except ValueError as error:  # orjson.JSONDecodeError subclasses json.JSONDecodeError
            raise JsonValueError(str(error)) from error

    return read_with_orjson


#: The reader this interpreter uses, chosen once at import.
_READER: Final[Callable[[str], object]] = select_reader(
    free_threaded=bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
    import_orjson=_import_orjson,
)


def read_json_value(text: str) -> object:
    """Read one JSON value with this interpreter's reader.

    Raises:
        JsonValueError: For text orjson would refuse.

    Examples:
        >>> read_json_value("[1, 2.5]")
        [1, 2.5]
    """
    return _READER(text)
