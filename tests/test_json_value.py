"""The stdlib JSON reader answers as orjson does, so ``--set`` values coerce the same everywhere."""

from __future__ import annotations

import importlib
import math
import sys
import sysconfig
from typing import TYPE_CHECKING

import pytest

from igittigitt.adapters.config.json_value import JsonValueError, read_with_stdlib, select_reader
from igittigitt.adapters.config.overrides import coerce_value

if TYPE_CHECKING:
    from collections.abc import Callable

# Every input where stdlib json and orjson differ by default, plus ordinary values and syntax
# errors as controls. Built as plain strings so the corpus is the same on every interpreter.
_CORPUS: tuple[str, ...] = (
    "true",
    "false",
    "null",
    "42",
    "-0",
    "-0.0",
    "3.14",
    "1e5",
    "1E-7",
    '"text"',
    '"caf\\u00e9"',
    '"a\\ud83d\\ude00b"',
    '{"a": [1, {"b": null}]}',
    '{"a": 1, "a": 2}',
    " \t[1]\n",
    "NaN",
    "Infinity",
    "-Infinity",
    '{"a": NaN}',
    "[1, Infinity]",
    "1e400",
    "-1e400",
    "[1e400]",
    '"\\ud800"',
    '"a\\udcffb"',
    '{"\\udc80": 1}',
    str(2**64 - 1),
    str(2**64),
    str(-(2**63)),
    str(-(2**63) - 1),
    "1" * 25,
    "1" * 5000,
    "[" * 1024 + "]" * 1024,
    "[" * 1025 + "]" * 1025,
    '{"a":' * 1024 + "1" + "}" * 1024,
    '{"a":' * 1025 + "1" + "}" * 1025,
    "[" * 1500 + "]" * 1500,
    "01",
    "1.",
    ".5",
    "+1",
    "0x10",
    "1_000",
    "tru",
    "[1,]",
    "",
    "DEBUG",
)


def _outcome(read: Callable[[str], object], text: str) -> tuple[str, object]:
    """Return what a reader makes of *text*: the value, or that it refused."""
    try:
        value = read(text)
    except JsonValueError:
        return ("refused", None)
    return ("value", value)


def _same(left: tuple[str, object], right: tuple[str, object]) -> bool:
    """Compare two outcomes by kind, type and value."""
    if left[0] != right[0]:
        return False
    a, b = left[1], right[1]
    if isinstance(a, float) and isinstance(b, float):
        return a == b or (math.isnan(a) and math.isnan(b))
    return type(a) is type(b) and a == b


@pytest.mark.os_agnostic
@pytest.mark.parametrize("text", _CORPUS, ids=lambda text: text if len(text) <= 24 else f"{text[:12]}..len{len(text)}")
def test_stdlib_reader_answers_as_orjson_does(text: str) -> None:
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        pytest.skip("importing orjson on a free-threaded build turns the GIL back on")
    orjson = pytest.importorskip("orjson")
    orjson_reader = select_reader(free_threaded=False, import_orjson=lambda: orjson)
    assert orjson_reader is not read_with_stdlib
    expected = _outcome(orjson_reader, text)
    actual = _outcome(read_with_stdlib, text)
    assert _same(actual, expected), f"stdlib {actual!r} != orjson {expected!r}"


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("NaN", "NaN"),
        ("Infinity", "Infinity"),
        ("1e400", "1e400"),
        ('"\\ud800"', '"\\ud800"'),
        (str(2**64), float(2**64)),
        ("[" * 1025 + "]" * 1025, "[" * 1025 + "]" * 1025),
        ("42", 42),
        ("DEBUG", "DEBUG"),
    ],
    ids=["nan", "infinity", "1e400", "lone-surrogate", "big-int", "too-deep", "int", "word"],
)
def test_coerce_value_keeps_the_released_answers(text: str, expected: object) -> None:
    # Runs with the reader this interpreter really uses: orjson below Python 3.14, the stdlib
    # reader from 3.14 and on every free-threaded build, so the CI matrix covers both.
    assert coerce_value(text) == expected


@pytest.mark.os_agnostic
def test_a_free_threaded_build_never_imports_orjson() -> None:
    def must_not_be_called() -> None:
        raise AssertionError("orjson was imported on a free-threaded build")

    assert select_reader(free_threaded=True, import_orjson=must_not_be_called) is read_with_stdlib


@pytest.mark.os_agnostic
def test_a_missing_orjson_selects_the_stdlib_reader() -> None:
    assert select_reader(free_threaded=False, import_orjson=lambda: None) is read_with_stdlib


@pytest.mark.os_agnostic
@pytest.mark.skipif(not sysconfig.get_config_var("Py_GIL_DISABLED"), reason="a free-threaded build only")
def test_the_gil_stays_off_after_igittigitt_and_its_cli_load() -> None:
    # A dependency without free-threading support turns the GIL back on when imported. Run this
    # WITHOUT PYTHON_GIL=0 or -X gil=0: forcing the GIL off makes the check assert nothing.
    importlib.import_module("igittigitt.adapters.cli.main")

    assert sys._is_gil_enabled() is False
