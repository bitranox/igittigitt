"""Parse and apply ``--set SECTION.KEY=VALUE`` CLI overrides to Config.

Contents:
    * :func:`parse_overrides` - parse a command line's ``--set`` values once, into
      :class:`ConfigOverrides`.
    * :func:`apply_overrides` - lay parsed overrides over a loaded Config.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

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

    @property
    def dotted_key(self) -> str:
        """The full key this override sets, ``section.key[.subkey...]``.

        Example:
            >>> ConfigOverride(section="s", key_path=("a", "b"), value=1).dotted_key
            's.a.b'
        """
        return ".".join((self.section, *self.key_path))


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
    """Lay one parsed override into the nested override mapping being built.

    Creates intermediate tables as needed. The value is copied, so a caller that changes the
    returned mapping cannot change the :class:`ConfigOverrides` it came from.

    Args:
        target: Mutable override mapping being built.
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
        # Always a table: ConfigOverrides refuses a key given both a value and keys under it
        # when it is built, so no override's value ever sits where another needs a table.
        node = cast("dict[str, object]", node.setdefault(part, {}))
    node[override.key_path[-1]] = deepcopy(override.value)


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


@dataclass(frozen=True, slots=True)
class ConfigOverrides:
    """The ``--set`` values of one command line, parsed and checked together.

    Built once, where the command line is read (:func:`parse_overrides`), and handed on as is:
    every consumer reads the nested tree or the dotted keys from here and none parses the raw
    strings again. Construction refuses a key that one entry gives a value and another puts a
    key under, so an instance never holds that contradiction.

    Attributes:
        entries: The parsed overrides in command-line order; for one key given twice the
            last entry wins.

    Raises:
        ValueError: Two entries conflict (one gives a key a value, another puts a key under it).

    Examples:
        >>> overrides = parse_overrides(("a.b=1", "a.c.d=x"))
        >>> overrides.tree(), sorted(overrides.keys)
        ({'a': {'b': 1, 'c': {'d': 'x'}}}, ['a.b', 'a.c.d'])
        >>> NO_OVERRIDES.is_empty
        True
    """

    entries: tuple[ConfigOverride, ...] = ()

    def __post_init__(self) -> None:
        """Refuse entries that give one key both a value and keys under it."""
        _refuse_conflicts([entry.dotted_key for entry in self.entries])

    @property
    def is_empty(self) -> bool:
        """Whether no ``--set`` was given."""
        return not self.entries

    @property
    def keys(self) -> frozenset[str]:
        """The dotted keys the overrides set (``section.key[.subkey...]``)."""
        return frozenset(entry.dotted_key for entry in self.entries)

    def tree(self) -> dict[str, dict[str, object]]:
        """Return a fresh nested override mapping, the form ``Config.with_overrides`` merges.

        Each call builds a new mapping with copied values, so changing it leaves this
        instance as it was.
        """
        tree: dict[str, dict[str, object]] = {}
        for entry in self.entries:
            _nest_override(tree, entry)
        return tree


NO_OVERRIDES: Final[ConfigOverrides] = ConfigOverrides()
"""The value of a command line without ``--set``."""


def parse_overrides(raw_overrides: tuple[str, ...]) -> ConfigOverrides:
    """Parse the ``--set`` values of one command line into :class:`ConfigOverrides`.

    Each value is parsed in command-line order, so the first malformed one is reported; only
    then are they checked against each other.

    Args:
        raw_overrides: Tuple of ``SECTION.KEY=VALUE`` strings from ``--set``.

    Returns:
        The parsed, checked overrides.

    Raises:
        ValueError: An override is malformed, or two of them conflict (one gives a key a
            value, another puts a key under it).

    Example:
        >>> sorted(parse_overrides(("a.b=1", "a.b=2")).keys)
        ['a.b']
        >>> parse_overrides(("a.b=1", "a.b=2")).tree()
        {'a': {'b': 2}}
    """
    return ConfigOverrides(entries=tuple(parse_override(raw) for raw in raw_overrides))


def apply_overrides(config: Config, overrides: ConfigOverrides) -> Config:
    """Deep-merge parsed ``--set`` overrides into a Config instance.

    Args:
        config: Original immutable Config from file/env layers.
        overrides: The parsed ``--set`` values.

    Returns:
        New Config instance with overrides applied, or the original if ``overrides`` is empty.

    Examples:
        >>> from lib_layered_config import Config
        >>> cfg = Config({"s": {"k": 1}}, {"s.k": {"layer": "default", "path": None, "key": "s.k"}})
        >>> result = apply_overrides(cfg, parse_overrides(("s.k=2",)))
        >>> result["s"]["k"]
        2
        >>> apply_overrides(cfg, NO_OVERRIDES) is cfg
        True
    """
    if overrides.is_empty:
        return config
    return config.with_overrides(overrides.tree())


__all__ = [
    "NO_OVERRIDES",
    "CoercedValue",
    "ConfigOverride",
    "ConfigOverrides",
    "apply_overrides",
    "coerce_value",
    "parse_override",
    "parse_overrides",
]
