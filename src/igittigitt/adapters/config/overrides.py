"""Parse and apply ``--set SECTION.KEY=VALUE`` CLI overrides to Config."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import orjson

if TYPE_CHECKING:
    from lib_layered_config import Config

CoercedValue = str | int | float | bool | None | list[object] | dict[str, object]
"""Union of types that :func:`coerce_value` can produce."""


@dataclass(frozen=True, slots=True)
class ConfigOverride:
    """A single parsed configuration override."""

    section: str
    key_path: tuple[str, ...]
    value: CoercedValue


def parse_override(raw: str) -> ConfigOverride:
    """Split a ``SECTION.KEY[.SUBKEY...]=VALUE`` string into a ConfigOverride.

    The first dot separates the top-level section from the key path.
    The first ``=`` separates the full dotted path from the value.
    Values are coerced via :func:`coerce_value`.

    Args:
        raw: Raw override string (e.g., ``lib_log_rich.console_level=DEBUG``).

    Returns:
        Parsed ConfigOverride with section, key_path tuple, and coerced value.

    Raises:
        ValueError: If the string lacks ``=``, has no dot in the key, or has
            empty section/key components.

    Examples:
        >>> override = parse_override("lib_log_rich.console_level=DEBUG")
        >>> override.section
        'lib_log_rich'
        >>> override.key_path
        ('console_level',)
        >>> override.value
        'DEBUG'

        >>> override = parse_override("lib_log_rich.payload_limits.max_chars=8192")
        >>> override.key_path
        ('payload_limits', 'max_chars')
        >>> override.value
        8192
    """
    if "=" not in raw:
        raise ValueError(f"Invalid override {raw!r}: must contain '='")

    path_part, value_str = raw.split("=", maxsplit=1)

    if "." not in path_part:
        raise ValueError(f"Invalid override {raw!r}: key must contain at least one dot (SECTION.KEY)")

    parts = path_part.split(".")
    section = parts[0]
    key_parts = tuple(parts[1:])

    if not section:
        raise ValueError(f"Invalid override {raw!r}: section name is empty")
    if not all(key_parts):
        raise ValueError(f"Invalid override {raw!r}: key path contains empty component")

    return ConfigOverride(
        section=section,
        key_path=key_parts,
        value=coerce_value(value_str),
    )


def coerce_value(raw: str) -> CoercedValue:
    """Coerce a raw string value using JSON parsing with string fallback.

    Attempts ``orjson.loads`` first (handling booleans, numbers, null, arrays,
    objects). Falls back to the raw string if JSON parsing fails.

    Args:
        raw: Raw value string from CLI.

    Returns:
        Parsed Python value (bool, int, float, None, list, dict) or the
        original string.

    Examples:
        >>> coerce_value("true")
        True
        >>> coerce_value("42")
        42
        >>> coerce_value("3.14")
        3.14
        >>> coerce_value("null")
        >>> coerce_value('["a","b"]')
        ['a', 'b']
        >>> coerce_value("DEBUG")
        'DEBUG'
        >>> coerce_value("")
        ''
    """
    if raw == "":
        return ""
    try:
        return orjson.loads(raw)
    except (orjson.JSONDecodeError, ValueError):
        return raw


def _nest_override(target: dict[str, dict[str, object]], override: ConfigOverride) -> None:
    """Build a nested override dict from a parsed ConfigOverride.

    Creates intermediate dicts as needed. The resulting dict structure
    is passed to ``Config.with_overrides()`` for merge.

    Args:
        target: Mutable override dictionary being built.
        override: Parsed override containing section, key_path, and value.

    Examples:
        >>> d: dict[str, dict[str, object]] = {}
        >>> _nest_override(d, ConfigOverride(section="s", key_path=("a",), value=2))
        >>> d["s"]["a"]
        2
        >>> d2: dict[str, dict[str, object]] = {}
        >>> _nest_override(d2, ConfigOverride(section="new", key_path=("x", "y"), value=3))
        >>> d2["new"]["x"]["y"]
        3
    """
    node: dict[str, object] = target.setdefault(override.section, {})
    for part in override.key_path[:-1]:
        # Always a table: nest_overrides refuses a key given both a value and keys under it
        # before nesting, so no override's value ever sits where another needs a table.
        node = cast("dict[str, object]", node.setdefault(part, {}))
    node[override.key_path[-1]] = override.value


def _refuse_conflicts(dotted_keys: list[str]) -> None:
    """Refuse a key that one override gives a value and another gives keys under.

    Either order is a contradiction on the command line: nesting ``a.b.c`` under the value
    of ``a.b`` fails, and ``a.b=1`` after ``a.b.c=2`` would silently drop the earlier one.

    Raises:
        ValueError: Naming the key and the override that puts a key under it.

    Examples:
        >>> _refuse_conflicts(["a.b", "a.bc", "a.b"])
        >>> _refuse_conflicts(["a.b.c", "a.b"])
        Traceback (most recent call last):
        ...
        ValueError: conflicting --set overrides: a.b is given a value and a.b.c puts a key under it
    """
    for key in dotted_keys:
        nested = next((other for other in dotted_keys if other.startswith(f"{key}.")), None)
        if nested is not None:
            raise ValueError(f"conflicting --set overrides: {key} is given a value and {nested} puts a key under it")


def nest_overrides(raw_overrides: tuple[str, ...]) -> tuple[dict[str, dict[str, object]], frozenset[str]]:
    """Parse ``--set`` values into the nested mapping they override, checking them together.

    Args:
        raw_overrides: Tuple of ``SECTION.KEY=VALUE`` strings from ``--set``.

    Returns:
        The nested override mapping and the dotted keys it sets. For one key given twice,
        the last value wins.

    Raises:
        ValueError: An override is malformed, or two of them conflict (one gives a key a
            value, another puts a key under it).

    Example:
        >>> tree, keys = nest_overrides(("a.b=1", "a.c.d=x"))
        >>> tree, sorted(keys)
        ({'a': {'b': 1, 'c': {'d': 'x'}}}, ['a.b', 'a.c.d'])
    """
    parsed = [parse_override(raw) for raw in raw_overrides]
    dotted_keys = [".".join((override.section, *override.key_path)) for override in parsed]
    _refuse_conflicts(dotted_keys)
    overrides: dict[str, dict[str, object]] = {}
    for override in parsed:
        _nest_override(overrides, override)
    return overrides, frozenset(dotted_keys)


def apply_overrides(config: Config, raw_overrides: tuple[str, ...]) -> Config:
    """Deep-merge CLI overrides into a Config instance.

    Parses each raw override string, builds a nested override dict,
    and delegates to ``Config.with_overrides()`` for the merge.

    Args:
        config: Original immutable Config from file/env layers.
        raw_overrides: Tuple of ``SECTION.KEY=VALUE`` strings from ``--set``.

    Returns:
        New Config instance with overrides applied, or the original if
        ``raw_overrides`` is empty.

    Raises:
        ValueError: If any override string is malformed, or two of them conflict.

    Examples:
        >>> from lib_layered_config import Config
        >>> cfg = Config({"s": {"k": 1}}, {"s.k": {"layer": "default", "path": None, "key": "s.k"}})
        >>> result = apply_overrides(cfg, ("s.k=2",))
        >>> result["s"]["k"]
        2
        >>> apply_overrides(cfg, ()) is cfg
        True
    """
    if not raw_overrides:
        return config

    overrides, _ = nest_overrides(raw_overrides)
    return config.with_overrides(overrides)


__all__ = [
    "CoercedValue",
    "ConfigOverride",
    "apply_overrides",
    "coerce_value",
    "nest_overrides",
    "parse_override",
]
