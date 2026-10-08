"""``config-deploy`` hands every permission decision to lib_layered_config.

The command passes what its command line said - ``--permissions``/``--no-permissions`` as
True/False/None, ``--dir-mode``/``--file-mode`` and the ``--set`` values of
``[lib_layered_config.default_permissions]`` - to ONE ``deploy_config`` call, and reads no
permission setting itself. The library reads the section from the bundled defaults, the
configuration files the deploy does not overwrite and the environment, never from ``.env``,
so neither a ``.env`` in the working directory nor a broken destination can change or block
a deploy. A refused setting exits 78 with one ``Error:`` line per problem.

A bare integer mode is refused because it is DECIMAL: TOML ``user_file = 400``,
``--set ...=400`` and an environment value ``400`` all arrive as the integer 400, which is
``0o620`` (group-writable), not the owner-read-only mode the digits suggest.
"""

from __future__ import annotations

import dataclasses
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pytest
from lib_layered_config import Config

from igittigitt import __init__conf__
from igittigitt.adapters.cli import cli
from igittigitt.adapters.config.deploy import deploy_configuration
from igittigitt.adapters.config.loader import get_default_config_path
from igittigitt.composition import AppServices, build_testing

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner

_SECTION = "lib_layered_config.default_permissions"
_KEY = f"{_SECTION}."

RecordedDeploys = Callable[[dict[str, Any]], tuple[list[dict[str, Any]], Callable[[], AppServices]]]


@pytest.fixture
def recorded_deploys() -> RecordedDeploys:
    """A testing-composition factory over a given configuration whose deploy records its arguments.

    Built on ``build_testing`` so its logging runtime is the quiet one: the production
    runtime's queued INFO lines would race into the stderr these tests count lines of.
    """

    def _make(config_data: dict[str, Any]) -> tuple[list[dict[str, Any]], Callable[[], AppServices]]:
        calls: list[dict[str, Any]] = []
        config = Config(config_data, {})

        def get_config(**_kwargs: Any) -> Config:
            return config

        def deploy(**kwargs: Any) -> list[Path]:
            calls.append(kwargs)
            return []

        def factory() -> AppServices:
            return dataclasses.replace(build_testing(), get_config=get_config, deploy_configuration=deploy)

        return calls, factory

    return _make


def _decision(call: dict[str, Any]) -> tuple[Any, ...]:
    return call["set_permissions"], call["dir_mode"], call["file_mode"], call["permission_overrides"]


# ======================== What the command hands to the deploy ========================


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ([], (None, None, None, None)),
        (["--permissions"], (True, None, None, None)),
        (["--no-permissions"], (False, None, None, None)),
        (["--dir-mode", "700"], (None, 0o700, None, None)),
        (["--dir-mode", "750", "--file-mode", "640"], (None, 0o750, 0o640, None)),
    ],
    ids=["no-options", "permissions", "no-permissions", "dir-mode", "both-modes"],
)
def test_one_deploy_call_carries_what_the_command_line_said(
    cli_runner: CliRunner, recorded_deploys: RecordedDeploys, options: list[str], expected: tuple[Any, ...]
) -> None:
    calls, factory = recorded_deploys({})

    result = cli_runner.invoke(cli, ["config-deploy", "--target", "app", "--target", "user", *options], obj=factory)

    assert result.exit_code == 0, result.output
    assert [_decision(call) for call in calls] == [expected]
    assert [target.value for target in calls[0]["targets"]] == ["app", "user"]


#: Configured sections the command used to read and act on. The library reads the section
#: itself now, so none of them reaches the command, valid or not.
_CONFIGURED = [
    {"lib_layered_config": {"default_permissions": {"user_file": "0o640"}}},
    {"lib_layered_config": {"default_permissions": {"enabled": False}}},
    {"lib_layered_config": {"default_permissions": {"user_directory": "0o777"}}},
    {"lib_layered_config": {"default_permissions": 5}},
]


@pytest.mark.os_agnostic
@pytest.mark.parametrize("config_data", _CONFIGURED, ids=["user-file", "enabled-false", "unsafe", "not-a-table"])
def test_the_command_reads_no_configured_permission_setting(
    cli_runner: CliRunner, recorded_deploys: RecordedDeploys, config_data: dict[str, Any]
) -> None:
    calls, factory = recorded_deploys(config_data)

    result = cli_runner.invoke(cli, ["config-deploy", "--target", "user"], obj=factory)

    assert result.exit_code == 0, result.output
    assert [_decision(call) for call in calls] == [(None, None, None, None)]


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ([f'{_KEY}user_directory="0o750"'], {"user_directory": "0o750"}),
        ([f"{_KEY}user_directory=0o750"], {"user_directory": "0o750"}),
        ([f"{_KEY}user_file=640"], {"user_file": 640}),
        ([f"{_KEY}enabled=false"], {"enabled": False}),
        ([f'{_KEY}user_file="0o640"', f'{_KEY}user_file="0o600"'], {"user_file": "0o600"}),
        ([f'{_SECTION}={{"user_file": "0o640"}}'], {"user_file": "0o640"}),
        ([f"{_KEY}user_file.x=1"], {"user_file": {"x": 1}}),
        ([f"{_SECTION}_x=1"], None),
    ],
    ids=["quoted", "unquoted", "decimal", "enabled", "last-wins", "whole-table", "deeper-key", "sibling-key"],
)
def test_a_set_of_the_section_reaches_the_deploy_unchanged_as_overrides(
    cli_runner: CliRunner, recorded_deploys: RecordedDeploys, settings: list[str], expected: dict[str, Any] | None
) -> None:
    """The same nested ``--set`` tree ``config`` shows; the library validates it."""
    calls, factory = recorded_deploys({})
    set_args = [arg for setting in settings for arg in ("--set", setting)]

    result = cli_runner.invoke(cli, [*set_args, "config-deploy", "--target", "user"], obj=factory)

    assert result.exit_code == 0, result.output
    assert [call["permission_overrides"] for call in calls] == [expected]


@pytest.mark.os_agnostic
@pytest.mark.parametrize(("value", "type_name"), [("5", "int"), ("null", "NoneType")], ids=["int", "null"])
def test_a_set_section_that_is_not_a_table_is_refused_before_the_deploy(
    cli_runner: CliRunner, recorded_deploys: RecordedDeploys, value: str, type_name: str
) -> None:
    calls, factory = recorded_deploys({})

    result = cli_runner.invoke(cli, ["--set", f"{_SECTION}={value}", "config-deploy", "--target", "user"], obj=factory)

    assert result.exit_code == 78, result.output
    assert [line for line in result.stderr.splitlines() if line.strip()] == [
        f"Error: {_SECTION}: must be a table, got {type_name} (source: override)"
    ]
    assert calls == []


@pytest.mark.os_agnostic
@pytest.mark.parametrize("modes", [["--dir-mode", "700"], ["--file-mode", "600"]])
def test_no_permissions_with_a_mode_is_a_usage_error(
    cli_runner: CliRunner, recorded_deploys: RecordedDeploys, modes: list[str]
) -> None:
    calls, factory = recorded_deploys({})

    result = cli_runner.invoke(cli, ["config-deploy", "--target", "user", "--no-permissions", *modes], obj=factory)

    assert result.exit_code == 2, result.output
    assert "--no-permissions cannot be combined with --dir-mode or --file-mode" in result.output
    assert calls == []


# ======================== Refusals, through the real library ========================


@pytest.fixture
def real_deploy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Callable[[], AppServices]:
    """The testing composition with the production deploy, every user-layer location under ``tmp_path``.

    The refusals below happen before anything is written; should one ever be accepted, the
    deploy lands in ``tmp_path`` rather than in the real user configuration directory.
    """
    for name in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "APPDATA", "LOCALAPPDATA"):
        monkeypatch.setenv(name, str(tmp_path))
    return lambda: dataclasses.replace(build_testing(), deploy_configuration=deploy_configuration)


#: Each ``--set`` value, and the text the one-line refusal must contain.
_REFUSED = [
    (f'{_KEY}user_directory="10000"', "user_directory: '10000' is outside 0..0o7777"),
    (f'{_KEY}user_directory="-1"', "user_directory: '-1' is not a plain octal literal"),
    (f'{_KEY}user_directory="7_5_0"', "user_directory: '7_5_0' is not a plain octal literal"),
    (f'{_KEY}user_directory="rwx"', "user_directory: 'rwx' is not a plain octal literal"),
    (f"{_KEY}user_file=400", "user_file: a bare integer is read as decimal (400 = 0o620)"),
    (f"{_KEY}user_file=444", "user_file: a bare integer is read as decimal (444 = 0o674)"),
    (f"{_KEY}user_file=640", "user_file: a bare integer is read as decimal (640 = 0o1200)"),
    (f"{_KEY}user_directory=448", 'write the mode as an octal string: "0o640" (quoted) in a file'),
    (f"{_KEY}user_directory=-1", "user_directory: a bare integer is read as decimal"),
    (f"{_KEY}user_directory=1.5", 'user_directory: expected a quoted octal string such as "0o640", got float'),
    (f"{_KEY}user_directory=true", 'user_directory: expected a quoted octal string such as "0o640", got bool'),
    (f'{_KEY}user_directory="0o777"', "user_directory: unsafe directory mode 0o777: group write (0o020); world write"),
    (f'{_KEY}user_directory="0o770"', "user_directory: unsafe directory mode 0o770: group write"),
    (f'{_KEY}user_file="0o620"', "user_file: unsafe file mode 0o620: group write"),
    (f'{_KEY}app_file="0o754"', "app_file: unsafe file mode 0o754: an execute bit on a file (0o110)"),
    (f'{_KEY}user_file="0o4600"', "user_file: unsafe file mode 0o4600: the setuid bit"),
    (f'{_KEY}app_file="0o400"', "app_file: unsafe file mode 0o400: no owner rw"),
    (f'{_KEY}enabled="maybe"', "default_permissions.enabled: must be true or false, got str 'maybe'"),
    # pydantic's lax bool would read each of these as a boolean; the setting is a real boolean.
    (f'{_KEY}enabled="no"', "default_permissions.enabled: must be true or false, got str 'no'"),
    (f'{_KEY}enabled="off"', "default_permissions.enabled: must be true or false, got str 'off'"),
    (f'{_KEY}enabled="false"', "default_permissions.enabled: must be true or false, got str 'false'"),
    (f"{_KEY}enabled=0", "default_permissions.enabled: must be true or false, got int 0"),
    (f"{_KEY}enabled=1", "default_permissions.enabled: must be true or false, got int 1"),
    (f"{_SECTION}=5", "default_permissions: must be a table, got int"),
    (f"{_SECTION}=null", "default_permissions: must be a table, got NoneType"),
    (f'{_KEY}user_dir="0o750"', "default_permissions: unknown setting 'user_dir'"),
    (f"{_KEY}user_file.x=1", 'user_file: expected a quoted octal string such as "0o640", got dict'),
]


@pytest.mark.os_agnostic
@pytest.mark.parametrize(("setting", "named"), _REFUSED, ids=[setting for setting, _ in _REFUSED])
def test_a_refused_set_is_a_one_line_config_error(
    cli_runner: CliRunner, real_deploy: Callable[[], AppServices], tmp_path: Path, setting: str, named: str
) -> None:
    result = cli_runner.invoke(cli, ["--set", setting, "config-deploy", "--target", "user"], obj=real_deploy)

    error_lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert result.exit_code == 78, result.output
    assert len(error_lines) == 1, result.stderr
    assert error_lines[0].startswith(f"Error: {_SECTION}")
    assert named in error_lines[0]
    assert error_lines[0].endswith("(source: override)")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.os_agnostic
def test_both_modes_do_not_get_past_a_refused_set(
    cli_runner: CliRunner, real_deploy: Callable[[], AppServices], tmp_path: Path
) -> None:
    """A bad ``--set`` is the command line's own mistake, so no hint offers a way around it."""
    result = cli_runner.invoke(
        cli,
        [
            "--set",
            f"{_KEY}user_file=640",
            "config-deploy",
            "--target",
            "user",
            "--dir-mode",
            "700",
            "--file-mode",
            "600",
        ],
        obj=real_deploy,
    )

    assert result.exit_code == 78, result.output
    assert "Hint:" not in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.os_agnostic
def test_a_non_boolean_enabled_is_not_reported_as_a_mode(
    cli_runner: CliRunner, real_deploy: Callable[[], AppServices]
) -> None:
    result = cli_runner.invoke(
        cli, ["--set", f'{_KEY}enabled="maybe"', "config-deploy", "--target", "user"], obj=real_deploy
    )

    assert result.exit_code == 78, result.output
    assert "enabled" in result.stderr
    assert "mode" not in result.stderr.lower()
    assert "errors.pydantic.dev" not in result.stderr


# ======================== End to end ========================
# Each subprocess argv is a literal list: an argv spliced from a variable is what ruff's S603
# flags as untrusted input, so what varies between cases goes through the environment or the
# working directory, or the case gets its own literal call.

_LINUX_ONLY = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="XDG_CONFIG_HOME locates the user layer on Linux"
)
_DOTENV_PREFIX = "LIB_LAYERED_CONFIG__DEFAULT_PERMISSIONS__"
_ENV_PREFIX = f"{__init__conf__.LAYEREDCONF_SLUG.upper().replace('-', '_')}___{_DOTENV_PREFIX}"


def _env(tmp_path: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    """The current environment with the user layer under ``tmp_path``."""
    return {**os.environ, "XDG_CONFIG_HOME": str(tmp_path), **(extra or {})}


def _stderr(completed: subprocess.CompletedProcess[bytes]) -> str:
    return completed.stderr.decode("utf-8", "replace")


def _user_dir(tmp_path: Path) -> Path:
    return tmp_path / __init__conf__.LAYEREDCONF_SLUG


def _user_modes(tmp_path: Path) -> tuple[int, int]:
    deployed = _user_dir(tmp_path)
    return stat.S_IMODE(deployed.stat().st_mode), stat.S_IMODE((deployed / "config.toml").stat().st_mode)


def _show_layered_config(tmp_path: Path) -> subprocess.CompletedProcess[bytes]:
    """``config`` for the ``lib_layered_config`` section, run from ``tmp_path`` like the deploys below."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "igittigitt",
            "config",
            "--format",
            "json",
            "--section",
            "lib_layered_config",
        ],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=_env(tmp_path),
    )


def _deploy_user(tmp_path: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    """``config-deploy --target user`` from ``tmp_path``, without options."""
    return subprocess.run(
        [sys.executable, "-m", "igittigitt", "config-deploy", "--target", "user"],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=_env(tmp_path, extra_env),
    )


@_LINUX_ONLY
def test_a_quoted_set_mode_is_applied_on_disk(tmp_path: Path) -> None:
    """``'"0o640"'`` is the JSON string ``"0o640"``."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "igittigitt",
            "--set",
            'lib_layered_config.default_permissions.user_directory="0o750"',
            "--set",
            'lib_layered_config.default_permissions.user_file="0o640"',
            "config-deploy",
            "--target",
            "user",
        ],
        capture_output=True,
        check=False,
        env=_env(tmp_path),
    )

    assert completed.returncode == 0, _stderr(completed)
    assert _user_modes(tmp_path) == (0o750, 0o640)


@_LINUX_ONLY
def test_an_unquoted_set_mode_is_applied_on_disk(tmp_path: Path) -> None:
    """Unquoted ``0o640`` is no JSON, so it arrives as the same string."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "igittigitt",
            "--set",
            "lib_layered_config.default_permissions.user_directory=0o750",
            "--set",
            "lib_layered_config.default_permissions.user_file=0o640",
            "config-deploy",
            "--target",
            "user",
        ],
        capture_output=True,
        check=False,
        env=_env(tmp_path),
    )

    assert completed.returncode == 0, _stderr(completed)
    assert _user_modes(tmp_path) == (0o750, 0o640)


@_LINUX_ONLY
def test_a_decimal_set_mode_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    """``640`` is valid JSON, so it arrives as the integer 640, which is 0o1200."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "igittigitt",
            "--set",
            "lib_layered_config.default_permissions.user_file=640",
            "config-deploy",
            "--target",
            "user",
        ],
        capture_output=True,
        check=False,
        env=_env(tmp_path),
    )

    stderr = _stderr(completed)
    assert completed.returncode == 78, stderr
    assert "user_file: a bare integer is read as decimal (640 = 0o1200)" in stderr
    assert "(source: override)" in stderr
    assert not _user_dir(tmp_path).exists()


def _existing_user_dir(tmp_path: Path) -> Path:
    """A user configuration directory that exists already, at 0o755."""
    _user_dir(tmp_path).mkdir()
    _user_dir(tmp_path).chmod(0o755)
    return _user_dir(tmp_path)


@_LINUX_ONLY
def test_a_deploy_sets_the_mode_of_an_existing_user_directory(tmp_path: Path) -> None:
    """The control for the next test: without the override, the directory does change."""
    directory = _existing_user_dir(tmp_path)

    completed = _deploy_user(tmp_path)

    assert completed.returncode == 0, _stderr(completed)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700


@_LINUX_ONLY
def test_a_set_enabled_false_turns_permission_setting_off(tmp_path: Path) -> None:
    """The library takes ``enabled`` from the override only because the command passes no bool."""
    directory = _existing_user_dir(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "igittigitt",
            "--set",
            "lib_layered_config.default_permissions.enabled=false",
            "config-deploy",
            "--target",
            "user",
        ],
        capture_output=True,
        check=False,
        env=_env(tmp_path),
    )

    assert completed.returncode == 0, _stderr(completed)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o755


@_LINUX_ONLY
def test_a_decimal_mode_from_the_environment_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    """End to end: the environment turns ``444`` into an integer, which would deploy 0o674."""
    completed = _deploy_user(tmp_path, {f"{_ENV_PREFIX}USER_FILE": "444"})

    stderr = _stderr(completed)
    assert completed.returncode == 78, stderr
    assert "user_file: a bare integer is read as decimal (444 = 0o674)" in stderr
    # A configured setting can be deployed past; the hint says how, in the CLI's own spelling.
    assert "Hint: to deploy anyway, pass both --dir-mode and --file-mode" in stderr
    assert "dir_mode" not in stderr
    assert not (_user_dir(tmp_path) / "config.toml").exists()


@_LINUX_ONLY
@pytest.mark.parametrize(("value", "expected_rc"), [("no", 78), ("false", 0)])
def test_enabled_from_the_environment_must_be_a_boolean_literal(tmp_path: Path, value: str, expected_rc: int) -> None:
    """End to end: ``false`` arrives as a boolean; ``no`` stays a string and is refused, not read as off."""
    completed = _deploy_user(tmp_path, {f"{_ENV_PREFIX}ENABLED": value})

    assert completed.returncode == expected_rc, _stderr(completed)


@_LINUX_ONLY
def test_a_dotenv_mode_does_not_decide_the_deployed_mode(tmp_path: Path) -> None:
    """Deploy never reads ``.env``: a mode in the working directory's ``.env`` changes nothing."""
    (tmp_path / ".env").write_text(f"{_DOTENV_PREFIX}USER_FILE=0o644\n", encoding="utf-8")
    assert '"user_file": "0o644"' in _show_layered_config(tmp_path).stdout.decode("utf-8", "replace")  # liveness

    completed = _deploy_user(tmp_path)

    assert completed.returncode == 0, _stderr(completed)
    assert _user_modes(tmp_path) == (0o700, 0o600)


@_LINUX_ONLY
def test_a_dotenv_mode_does_not_decide_the_deployed_mode_beside_a_set(tmp_path: Path) -> None:
    """With a ``--set`` of the section the library reads it, still without ``.env``."""
    (tmp_path / ".env").write_text(f"{_DOTENV_PREFIX}USER_FILE=0o644\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "igittigitt",
            "--set",
            'lib_layered_config.default_permissions.user_directory="0o750"',
            "config-deploy",
            "--target",
            "user",
        ],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=_env(tmp_path),
    )

    assert completed.returncode == 0, _stderr(completed)
    assert _user_modes(tmp_path) == (0o750, 0o600)


@_LINUX_ONLY
def test_a_dotenv_enabled_false_does_not_turn_permission_setting_off(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(f"{_DOTENV_PREFIX}ENABLED=false\n", encoding="utf-8")
    assert '"enabled": false' in _show_layered_config(tmp_path).stdout.decode("utf-8", "replace")  # liveness

    completed = _deploy_user(tmp_path)

    assert completed.returncode == 0, _stderr(completed)
    assert _user_modes(tmp_path) == (0o700, 0o600)


@_LINUX_ONLY
def test_a_malformed_dotenv_does_not_block_the_deploy(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("NOT A KEY VALUE LINE\n", encoding="utf-8")
    assert _show_layered_config(tmp_path).returncode == 78  # liveness: the command's own read fails on it

    completed = _deploy_user(tmp_path)

    assert completed.returncode == 0, _stderr(completed)
    assert (_user_dir(tmp_path) / "config.toml").is_file()


def _force_deploy_user(tmp_path: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "igittigitt", "config-deploy", "--target", "user", "--force"],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=_env(tmp_path),
    )


@_LINUX_ONLY
def test_a_broken_deployed_user_file_is_replaced_by_a_forced_deploy(tmp_path: Path) -> None:
    """The destination a deploy overwrites is outside its read, so its breakage cannot block it."""
    _user_dir(tmp_path).mkdir()
    (_user_dir(tmp_path) / "config.toml").write_text("[broken\n", encoding="utf-8")
    assert _show_layered_config(tmp_path).returncode == 78  # liveness: the file is broken

    completed = _force_deploy_user(tmp_path)

    assert completed.returncode == 0, _stderr(completed)
    assert (_user_dir(tmp_path) / "config.toml").read_bytes() == get_default_config_path().read_bytes()


@_LINUX_ONLY
def test_a_decimal_mode_in_the_deployed_user_file_does_not_block_its_replacement(tmp_path: Path) -> None:
    """``user_file = 400`` sits in the very file ``--force`` overwrites, so the library never reads it."""
    _user_dir(tmp_path).mkdir()
    (_user_dir(tmp_path) / "config.toml").write_text(
        "[lib_layered_config.default_permissions]\nuser_file = 400\n", encoding="utf-8"
    )
    assert '"user_file": 400' in _show_layered_config(tmp_path).stdout.decode("utf-8", "replace")  # liveness

    completed = _force_deploy_user(tmp_path)

    assert completed.returncode == 0, _stderr(completed)
    assert (_user_dir(tmp_path) / "config.toml").read_bytes() == get_default_config_path().read_bytes()
    assert _user_modes(tmp_path) == (0o700, 0o600)
