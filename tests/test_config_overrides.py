"""``--set`` overrides: values given together are checked together.

One override can give a key a value while another puts a key under it. Nesting them one
after the other went wrong in either order: a ``TypeError`` that escaped the CLI, or the
earlier override silently dropped. They are refused as a contradiction instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from lib_layered_config import Config

from igittigitt.adapters.cli import cli
from igittigitt.adapters.config.overrides import apply_overrides, nest_overrides
from igittigitt.composition import build_testing

if TYPE_CHECKING:
    from click.testing import CliRunner


def _empty_config() -> Config:
    return Config({}, {})


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    "overrides",
    [("a.b=1", "a.b.c=2"), ("a.b.c=2", "a.b=1"), ('a.b={"c": 1}', "a.b.d=2"), ("a.b.c=1", "a.x=0", "a.b=2")],
    ids=["value-then-key-under-it", "key-under-it-then-value", "json-table-then-key-under-it", "not-adjacent"],
)
def test_apply_overrides_refuses_a_key_given_both_a_value_and_keys_under_it(overrides: tuple[str, ...]) -> None:
    """Either order used to go wrong: a TypeError, or the earlier override silently dropped."""
    with pytest.raises(ValueError, match=r"conflicting --set overrides: a\.b is given a value and a\.b\."):
        apply_overrides(_empty_config(), overrides)


@pytest.mark.os_agnostic
def test_apply_overrides_lets_the_last_of_two_values_for_one_key_win() -> None:
    result = apply_overrides(_empty_config(), ("a.b=1", "a.b=2"))

    assert result["a"]["b"] == 2


@pytest.mark.os_agnostic
def test_apply_overrides_keeps_sibling_keys_that_share_a_prefix_of_letters() -> None:
    """``a.b`` and ``a.bc`` are siblings, not a value and a key under it."""
    result = apply_overrides(_empty_config(), ("a.b=1", "a.bc.d=2"))

    assert result["a"] == {"b": 1, "bc": {"d": 2}}


@pytest.mark.os_agnostic
def test_nest_overrides_returns_the_tree_and_the_dotted_keys_it_sets() -> None:
    tree, keys = nest_overrides(("a.b=1", "a.c.d=x"))

    assert tree == {"a": {"b": 1, "c": {"d": "x"}}}
    assert keys == frozenset({"a.b", "a.c.d"})


@pytest.mark.os_agnostic
@pytest.mark.parametrize("command", [["info"], ["config"]], ids=["info", "config"])
@pytest.mark.parametrize(
    "overrides", [("a.b=1", "a.b.c=2"), ("a.b.c=2", "a.b=1")], ids=["value-first", "key-under-it-first"]
)
def test_conflicting_set_overrides_are_a_usage_error(
    cli_runner: CliRunner, command: list[str], overrides: tuple[str, str]
) -> None:
    """The first order used to escape as a TypeError; the second dropped ``a.b.c`` and exited 0."""
    args = ["--set", overrides[0], "--set", overrides[1], *command]

    result = cli_runner.invoke(cli, args, obj=build_testing)

    assert result.exit_code == 2, result.output
    assert "conflicting --set overrides: a.b is given a value and a.b.c" in result.output
