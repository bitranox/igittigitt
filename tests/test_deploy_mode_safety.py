"""``--dir-mode`` / ``--file-mode`` are validated before anything is written.

A deployed configuration file can hold secrets, so a mode reaches ``chmod`` only when it is a
plain octal literal inside 0..0o7777 and is safe for such a file: no setuid, setgid
or sticky bit, no group or world write, no execute bit on a file, and the owner keeps the
access it needs (rwx on a directory, rw on a file). Group write matters as much as world
write: on macOS every local account shares the group ``staff``. ``--dir-mode -1`` used to
reach ``chmod(-1)`` and leave the directory at 0o7777. Every refusal is a click usage error
(exit 2) raised before ``deploy_configuration`` is called. The rule is lib_layered_config's
``DeployMode``, the one the library applies to configured modes too.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

import pytest

from igittigitt.adapters.cli import cli
from igittigitt.composition import AppServices, build_testing

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from click.testing import CliRunner

#: Each parses under a bare ``int(value, 8)`` although it is no mode literal: int() strips
#: whitespace, accepts ``_`` separators and converts non-ASCII decimal digits.
_ONLY_THE_LITERAL_CHECK_CATCHES = (
    " 750",
    "7_5_0",
    "\uff17\uff15\uff10",  # fullwidth "750"
    "\u0667\u0665\u0660",  # Arabic-Indic "750"
)
_MALFORMED = (
    "-1",
    "+7",
    "0x1ff",
    "0O750",
    "",
    "0o",
    "abc",
    "9",
    *_ONLY_THE_LITERAL_CHECK_CATCHES,
)
_OUT_OF_RANGE = ("10000", "77777777777777777777")
#: Each malformed or out-of-range literal, and the reason lib_layered_config gives for it.
_REFUSED_LITERALS = (
    *((mode, "is not a plain octal literal") for mode in _MALFORMED),
    *((mode, "is outside 0..0o7777") for mode in _OUT_OF_RANGE),
)
#: Parse cleanly but are unsafe, each with the phrase the refusal must name.
_UNSAFE_DIR_MODES = (
    ("7777", "setuid"),
    ("4750", "setuid"),
    ("2750", "setgid"),
    ("1750", "sticky"),
    ("777", "world write"),
    ("770", "group write"),
    ("775", "group write"),
    ("0o730", "group write"),
    ("0", "owner rwx"),
    ("650", "owner rwx"),
)
_UNSAFE_FILE_MODES = (
    ("4640", "setuid"),
    ("666", "world write"),
    ("660", "group write"),
    ("620", "group write"),
    ("700", "execute"),
    ("740", "execute"),
    ("641", "execute"),
    ("0o674", "group write"),
    ("0", "owner rw"),
    ("440", "owner rw"),
)
#: Leading zeros are dropped before the range check, so "0000750" is 0o750.
_SAFE_DIR_MODES = (
    ("750", 0o750),
    ("0o750", 0o750),
    ("700", 0o700),
    ("0o710", 0o710),
    ("755", 0o755),
    ("0000750", 0o750),
)
_SAFE_FILE_MODES = (("640", 0o640), ("600", 0o600), ("0o644", 0o644))


@pytest.fixture
def recorded_deploys() -> tuple[list[dict[str, Any]], Callable[[], AppServices]]:
    """A testing-composition factory whose deploy records its keyword arguments and writes nothing."""
    calls: list[dict[str, Any]] = []

    def deploy(**kwargs: Any) -> list[Path]:
        calls.append(kwargs)
        return []

    return calls, lambda: dataclasses.replace(build_testing(), deploy_configuration=deploy)


def _deploy(cli_runner: CliRunner, factory: Callable[[], AppServices], *options: str) -> Any:
    return cli_runner.invoke(cli, ["config-deploy", "--target", "user", *options], obj=factory)


@pytest.mark.os_agnostic
@pytest.mark.parametrize("option", ["--dir-mode", "--file-mode"])
@pytest.mark.parametrize(("mode", "reason"), _REFUSED_LITERALS)
def test_a_malformed_or_out_of_range_mode_is_a_usage_error(
    cli_runner: CliRunner,
    recorded_deploys: tuple[list[dict[str, Any]], Callable[[], AppServices]],
    option: str,
    mode: str,
    reason: str,
) -> None:
    calls, factory = recorded_deploys

    result = _deploy(cli_runner, factory, option, mode)

    assert result.exit_code == 2, result.output
    assert reason in result.output
    assert calls == []


@pytest.mark.os_agnostic
@pytest.mark.parametrize(("mode", "named"), _UNSAFE_DIR_MODES)
def test_an_unsafe_dir_mode_is_refused_naming_the_bit(
    cli_runner: CliRunner,
    recorded_deploys: tuple[list[dict[str, Any]], Callable[[], AppServices]],
    mode: str,
    named: str,
) -> None:
    calls, factory = recorded_deploys

    result = _deploy(cli_runner, factory, "--dir-mode", mode)

    assert result.exit_code == 2, result.output
    assert named in result.output
    assert calls == []


@pytest.mark.os_agnostic
@pytest.mark.parametrize(("mode", "named"), _UNSAFE_FILE_MODES)
def test_an_unsafe_file_mode_is_refused_naming_the_bit(
    cli_runner: CliRunner,
    recorded_deploys: tuple[list[dict[str, Any]], Callable[[], AppServices]],
    mode: str,
    named: str,
) -> None:
    calls, factory = recorded_deploys

    result = _deploy(cli_runner, factory, "--file-mode", mode)

    assert result.exit_code == 2, result.output
    assert named in result.output
    assert calls == []


@pytest.mark.os_agnostic
@pytest.mark.parametrize(("mode", "expected"), _SAFE_DIR_MODES)
def test_a_safe_dir_mode_reaches_the_deploy(
    cli_runner: CliRunner,
    recorded_deploys: tuple[list[dict[str, Any]], Callable[[], AppServices]],
    mode: str,
    expected: int,
) -> None:
    calls, factory = recorded_deploys

    result = _deploy(cli_runner, factory, "--dir-mode", mode)

    assert result.exit_code == 0, result.output
    assert [call["dir_mode"] for call in calls] == [expected]


@pytest.mark.os_agnostic
@pytest.mark.parametrize(("mode", "expected"), _SAFE_FILE_MODES)
def test_a_safe_file_mode_reaches_the_deploy(
    cli_runner: CliRunner,
    recorded_deploys: tuple[list[dict[str, Any]], Callable[[], AppServices]],
    mode: str,
    expected: int,
) -> None:
    calls, factory = recorded_deploys

    result = _deploy(cli_runner, factory, "--file-mode", mode)

    assert result.exit_code == 0, result.output
    assert [call["file_mode"] for call in calls] == [expected]
