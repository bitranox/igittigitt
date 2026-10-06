"""A configuration that cannot be loaded: who reports it, and who still runs.

The root group loads the configuration before any subcommand's options are parsed, so it
cannot report a failure in the form the subcommand would, and it must not block a command
that never reads the configuration: ``config-deploy`` is how a broken file gets replaced,
and ``info`` or ``--help`` have to work meanwhile. The root records the failure; a command
that reads the configuration refuses with exit 78 and one stderr line naming it. Every way
loading can fail (a broken or invalid file, an unreadable file) takes that path; ``--traceback``
adds the loader's traceback. What the command line itself gets wrong - a malformed ``--set``,
an invalid ``--profile`` name - is a usage error (exit 2) for every command, checked before
loading, so a load failure cannot hide it. Any other exception from the loader is a bug and is
not dressed up as a configuration error.

``config-deploy`` reads nothing from the configuration the root loaded: it hands its command
line to lib_layered_config, which reads the permission settings itself, without ``.env`` and
without the files the deploy overwrites. A configuration that did not load therefore never
blocks it, whatever its options; a permission setting the library refuses exits 78 with one
``Error:`` line per problem and, when the command line can get past it, a hint in the CLI's own
spelling.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import stat
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import pytest
from lib_layered_config import Config, ConfigError, DeployPermissionsError, PermissionProblem

from igittigitt import __init__conf__
from igittigitt.adapters.cli import cli
from igittigitt.composition import AppServices, build_production, build_testing

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from click.testing import CliRunner

BROKEN_TOML = "Invalid TOML in /etc/xdg/app/config.toml: expected a right bracket"
BROKEN_PROFILE_TOML = "Invalid TOML in /etc/xdg/app/profile/prod/config.toml"
UNREADABLE = PermissionError(13, "Permission denied", "/etc/xdg/app/config.toml")

#: Each command with the arguments that get it past click's own option parsing. A command
#: added without an entry fails ``test_every_command_is_classified``, so nobody can add one
#: that silently reads an empty configuration after a load failure.
#: ``check`` and ``filter`` read their ``[performance]`` knobs from it.
NEEDS_CONFIG: dict[str, list[str]] = {
    "check": ["check", "-r", "*.log", "a.log"],
    "config": ["config"],
    "filter": ["filter", "-r", "*.log", "a.log"],
}
RUNS_WITHOUT_CONFIG: dict[str, list[str]] = {
    "config-deploy": ["config-deploy", "--target", "user"],
    "info": ["info"],
}
#: Covered by their own tests below: one writes into a directory, one replaces the logging
#: runtime.
OTHER = ("config-generate-examples", "logdemo")


def _failing_config(error: Exception) -> Callable[[], AppServices]:
    def get_config(**_kwargs: Any) -> Config:
        raise error

    return lambda: dataclasses.replace(build_testing(), get_config=get_config)


@pytest.mark.os_agnostic
def test_every_command_is_classified() -> None:
    assert set(NEEDS_CONFIG) | set(RUNS_WITHOUT_CONFIG) | set(OTHER) == set(cli.commands)


@pytest.mark.os_agnostic
@pytest.mark.parametrize("args", NEEDS_CONFIG.values(), ids=NEEDS_CONFIG.keys())
@pytest.mark.parametrize(
    ("error", "message"),
    [(ConfigError(BROKEN_TOML), BROKEN_TOML), (UNREADABLE, str(UNREADABLE))],
    ids=["broken-file", "unreadable-file"],
)
def test_a_command_that_reads_the_config_refuses_with_exit_78(
    cli_runner: CliRunner, args: list[str], error: Exception, message: str
) -> None:
    result = cli_runner.invoke(cli, args, obj=_failing_config(error))

    assert result.exit_code == 78, result.output
    assert f"Error: {message}" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.os_agnostic
@pytest.mark.parametrize("args", RUNS_WITHOUT_CONFIG.values(), ids=RUNS_WITHOUT_CONFIG.keys())
def test_a_command_that_does_not_read_the_config_still_runs(cli_runner: CliRunner, args: list[str]) -> None:
    result = cli_runner.invoke(cli, args, obj=_failing_config(ConfigError(BROKEN_TOML)))

    assert result.exit_code == 0, result.output


def _recording_failing_config(error: Exception) -> tuple[list[dict[str, Any]], Callable[[], AppServices]]:
    """A failing configuration whose deploy records its keyword arguments and writes nothing."""
    calls: list[dict[str, Any]] = []

    def get_config(**_kwargs: Any) -> Config:
        raise error

    def deploy(**kwargs: Any) -> list[Path]:
        calls.append(kwargs)
        return []

    return calls, lambda: dataclasses.replace(build_testing(), get_config=get_config, deploy_configuration=deploy)


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ([], (None, None, None)),
        (["--permissions"], (True, None, None)),
        (["--no-permissions"], (False, None, None)),
        (["--dir-mode", "750"], (None, 0o750, None)),
        (["--dir-mode", "750", "--file-mode", "640"], (None, 0o750, 0o640)),
    ],
    ids=["no-options", "permissions-on", "no-permissions", "dir-mode-only", "both-modes"],
)
def test_config_deploy_runs_whatever_its_options_when_the_config_did_not_load(
    cli_runner: CliRunner, options: list[str], expected: tuple[bool | None, int | None, int | None]
) -> None:
    """The library reads the permission settings itself; the root's failed load is not its business."""
    calls, factory = _recording_failing_config(ConfigError(BROKEN_TOML))

    result = cli_runner.invoke(cli, ["config-deploy", "--target", "user", *options], obj=factory)

    assert result.exit_code == 0, result.output
    assert BROKEN_TOML not in result.stderr
    assert [(call["set_permissions"], call["dir_mode"], call["file_mode"]) for call in calls] == [expected]


def _refusing_deploy(error: DeployPermissionsError) -> Callable[[], AppServices]:
    def deploy(**_kwargs: Any) -> list[Path]:
        raise error

    return lambda: dataclasses.replace(build_testing(), deploy_configuration=deploy)


_PROBLEMS = (
    PermissionProblem("lib_layered_config.default_permissions.user_file", "a bare integer", "/etc/xdg/app/config.toml"),
    PermissionProblem("lib_layered_config.default_permissions.enabled", "must be true or false, got str 'no'", "env"),
)


@pytest.mark.os_agnostic
def test_a_library_refusal_is_one_error_line_per_problem_then_the_cli_hint(cli_runner: CliRunner) -> None:
    """The library's hint names its Python parameters (dir_mode); the CLI replaces it with its options."""
    error = DeployPermissionsError(_PROBLEMS, hint="to deploy anyway, give both modes (dir_mode and file_mode)")

    result = cli_runner.invoke(cli, ["config-deploy", "--target", "user"], obj=_refusing_deploy(error))

    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert result.exit_code == 78, result.output
    assert lines[:2] == [f"Error: {problem}" for problem in _PROBLEMS]
    assert len(lines) == 3, result.stderr
    assert lines[2].startswith("Hint: to deploy anyway, pass both --dir-mode and --file-mode")
    assert "--no-permissions also deploys, but leaves every mode to the umask" in lines[2]
    assert "dir_mode" not in result.stderr


@pytest.mark.os_agnostic
def test_a_library_refusal_without_a_hint_offers_none(cli_runner: CliRunner) -> None:
    """A refused --set has no way around it on the command line, so the library gives no hint."""
    error = DeployPermissionsError(_PROBLEMS[:1])

    result = cli_runner.invoke(cli, ["config-deploy", "--target", "user"], obj=_refusing_deploy(error))

    assert result.exit_code == 78, result.output
    assert [line for line in result.stderr.splitlines() if line.strip()] == [f"Error: {_PROBLEMS[0]}"]


@pytest.mark.os_agnostic
@pytest.mark.parametrize("refused", [True, False], ids=["refused", "deploys"])
def test_config_deploy_logs_a_deploy_only_after_it_happened(
    cli_runner: CliRunner, caplog: pytest.LogCaptureFixture, refused: bool
) -> None:
    """An INFO line before the call would tell the log a deploy happened that the library refused."""
    factory = _refusing_deploy(DeployPermissionsError(_PROBLEMS[:1])) if refused else build_testing

    with caplog.at_level(logging.INFO):
        result = cli_runner.invoke(cli, ["config-deploy", "--target", "user"], obj=factory)

    announced = [record for record in caplog.records if record.getMessage() == "Deployed configuration"]
    assert result.exit_code == (78 if refused else 0), result.output
    assert len(announced) == (0 if refused else 1)


@pytest.mark.os_agnostic
def test_config_generate_examples_still_runs(cli_runner: CliRunner, tmp_path: Path) -> None:
    args = ["config-generate-examples", "--destination", str(tmp_path)]
    result = cli_runner.invoke(cli, args, obj=_failing_config(ConfigError(BROKEN_TOML)))

    assert result.exit_code == 0, result.output


@pytest.mark.os_agnostic
@pytest.mark.parametrize("args", [["config-deploy", "--help"], []], ids=["subcommand-help", "bare-group"])
def test_help_works_while_the_config_is_broken(cli_runner: CliRunner, args: list[str]) -> None:
    result = cli_runner.invoke(cli, args, obj=_failing_config(ConfigError(BROKEN_TOML)))

    assert result.exit_code == 0, result.output
    assert "Usage" in result.stdout


@pytest.mark.os_agnostic
def test_a_malformed_set_is_still_a_usage_error(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["--set", "no-equals-sign", "info"], obj=build_testing)

    assert result.exit_code == 2, result.output


@pytest.mark.os_agnostic
@pytest.mark.parametrize("command", [["info"], ["config"]], ids=["info", "config"])
def test_a_malformed_set_is_a_usage_error_even_when_the_config_does_not_load(
    cli_runner: CliRunner, command: list[str]
) -> None:
    """Checked before loading, so a broken file cannot hide the command line's own mistake."""
    args = ["--set", "no-equals-sign", *command]
    result = cli_runner.invoke(cli, args, obj=_failing_config(ConfigError(BROKEN_TOML)))

    assert result.exit_code == 2, result.output
    assert "no-equals-sign" in result.output


@pytest.mark.os_agnostic
@pytest.mark.parametrize("command", [["info"], ["config"]], ids=["info", "config"])
@pytest.mark.parametrize("loads", [True, False], ids=["config-loads", "config-broken"])
def test_conflicting_set_overrides_are_a_usage_error(cli_runner: CliRunner, command: list[str], loads: bool) -> None:
    """``--set a.b=1 --set a.b.c=2`` used to escape as a TypeError (exit 22 through main)."""
    factory = build_testing if loads else _failing_config(ConfigError(BROKEN_TOML))
    result = cli_runner.invoke(cli, ["--set", "a.b=1", "--set", "a.b.c=2", *command], obj=factory)

    assert result.exit_code == 2, result.output
    assert "conflicting --set overrides: a.b is given a value and a.b.c" in result.output


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    "args",
    [
        ["--profile", "../x", "info"],
        ["config", "--profile", "../x"],
        ["config-deploy", "--target", "user", "--no-permissions", "--profile", "../x"],
    ],
    ids=["root-info", "config-option", "config-deploy-option"],
)
def test_an_invalid_profile_name_is_a_usage_error_for_every_command(cli_runner: CliRunner, args: list[str]) -> None:
    result = cli_runner.invoke(cli, args, obj=build_testing)

    assert result.exit_code == 2, result.output
    assert "../x" in result.output


@pytest.mark.os_agnostic
def test_a_bug_in_the_loader_is_not_reported_as_a_configuration_error(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["config"], obj=_failing_config(ValueError("a bug, not a config file")))

    assert result.exit_code != 78, result.output
    assert isinstance(result.exception, ValueError)


@pytest.fixture
def non_utf8_env_file(tmp_path: Path) -> Path:
    env_file = tmp_path / "latin1.env"
    env_file.write_bytes(b"A=\xff\xfe\n")
    return env_file


@pytest.fixture
def real_loader(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, clear_config_cache: None) -> Callable[[], AppServices]:
    """The testing composition over the production loader, with an empty user layer.

    A ``.env`` file that is not UTF-8 is lib_layered_config's to report: it raises its own
    ConfigError naming the file, so the CLI records it like any other broken file.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return lambda: dataclasses.replace(build_testing(), get_config=build_production().get_config)


@pytest.mark.os_agnostic
@pytest.mark.parametrize("args", RUNS_WITHOUT_CONFIG.values(), ids=RUNS_WITHOUT_CONFIG.keys())
def test_a_command_that_does_not_read_the_config_runs_past_a_non_utf8_env_file(
    cli_runner: CliRunner, real_loader: Callable[[], AppServices], non_utf8_env_file: Path, args: list[str]
) -> None:
    argv = ["--env-file", str(non_utf8_env_file), *args]
    result = cli_runner.invoke(cli, argv, obj=real_loader)

    assert result.exit_code == 0, result.output


@pytest.mark.os_agnostic
@pytest.mark.parametrize("args", NEEDS_CONFIG.values(), ids=NEEDS_CONFIG.keys())
def test_a_non_utf8_env_file_is_a_configuration_error_naming_the_file(
    cli_runner: CliRunner, real_loader: Callable[[], AppServices], non_utf8_env_file: Path, args: list[str]
) -> None:
    argv = ["--env-file", str(non_utf8_env_file), *args]
    result = cli_runner.invoke(cli, argv, obj=real_loader)

    error_lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert result.exit_code == 78, result.output
    assert len(error_lines) == 1, result.stderr
    assert f"{non_utf8_env_file} is not valid UTF-8" in error_lines[0]


@pytest.mark.os_agnostic
def test_traceback_shows_why_the_config_did_not_load(cli_runner: CliRunner, managed_traceback_state: None) -> None:
    def get_config(**_kwargs: Any) -> Config:
        try:
            raise OSError("the underlying cause")
        except OSError as cause:
            raise ConfigError(BROKEN_TOML) from cause

    services = dataclasses.replace(build_testing(), get_config=get_config)
    result = cli_runner.invoke(cli, ["--traceback", "config"], obj=lambda: services)

    assert result.exit_code == 78, result.output
    assert "Traceback" in result.stderr
    assert "OSError: the underlying cause" in result.stderr
    assert BROKEN_TOML in result.stderr


@pytest.mark.os_agnostic
def test_a_profile_given_to_config_itself_fails_like_one_given_to_the_root(cli_runner: CliRunner) -> None:
    def get_config(*, profile: str | None = None, **_kwargs: Any) -> Config:
        if profile == "prod":
            raise ConfigError(BROKEN_PROFILE_TOML)
        return Config({}, {})

    services = dataclasses.replace(build_testing(), get_config=get_config)
    result = cli_runner.invoke(cli, ["config", "--profile", "prod"], obj=lambda: services)

    assert result.exit_code == 78, result.output
    assert f"Error: {BROKEN_PROFILE_TOML}" in result.stderr


@pytest.mark.os_agnostic
def test_a_profile_given_to_config_itself_keeps_the_root_env_file(cli_runner: CliRunner, tmp_path: Path) -> None:
    env_file = tmp_path / "app.env"
    env_file.write_text("", encoding="utf-8")
    calls: list[tuple[str | None, str | None]] = []

    def get_config(*, profile: str | None = None, dotenv_path: str | None = None, **_kwargs: Any) -> Config:
        calls.append((profile, dotenv_path))
        return Config({}, {})

    services = dataclasses.replace(build_testing(), get_config=get_config)
    args = ["--env-file", str(env_file), "config", "--profile", "prod"]
    result = cli_runner.invoke(cli, args, obj=lambda: services)

    assert result.exit_code == 0, result.output
    assert calls == [(None, str(env_file)), ("prod", str(env_file))]


@pytest.fixture
def broken_user_config_env(tmp_path: Path) -> dict[str, str]:
    """An environment whose user layer holds a config.toml that does not parse."""
    config_dir = tmp_path / __init__conf__.LAYEREDCONF_SLUG
    config_dir.mkdir()
    (config_dir / "config.toml").write_text("broken = [\n", encoding="utf-8")
    return {**os.environ, "XDG_CONFIG_HOME": str(tmp_path)}


_LINUX_ONLY = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="XDG_CONFIG_HOME locates the user layer on Linux"
)


def _stderr_of(completed: subprocess.CompletedProcess[bytes]) -> str:
    stderr = completed.stderr.decode("utf-8", "replace")
    assert "UnicodeDecodeError" not in stderr
    return stderr


@_LINUX_ONLY
def test_a_real_non_utf8_env_file_does_not_stop_info(tmp_path: Path, non_utf8_env_file: Path) -> None:
    """End to end, in a process of its own, through the real loader."""
    completed = subprocess.run(
        [sys.executable, "-m", "igittigitt", "--env-file", "latin1.env", "info"],
        capture_output=True,
        check=False,
        cwd=non_utf8_env_file.parent,
        env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "xdg")},
    )

    assert completed.returncode == 0, _stderr_of(completed)


@_LINUX_ONLY
def test_a_real_non_utf8_env_file_refuses_config_with_78(tmp_path: Path, non_utf8_env_file: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "igittigitt", "--env-file", "latin1.env", "config"],
        capture_output=True,
        check=False,
        cwd=non_utf8_env_file.parent,
        env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "xdg")},
    )

    stderr = _stderr_of(completed)
    assert completed.returncode == 78, stderr
    assert "latin1.env is not valid UTF-8" in stderr


@_LINUX_ONLY
def test_a_real_non_utf8_env_file_does_not_stop_config_deploy(tmp_path: Path, non_utf8_env_file: Path) -> None:
    """The command that replaces a broken configuration must not be blocked by it."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "igittigitt",
            "--env-file",
            "latin1.env",
            "config-deploy",
            "--target",
            "user",
        ],
        capture_output=True,
        check=False,
        cwd=non_utf8_env_file.parent,
        env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "xdg")},
    )

    assert completed.returncode == 0, _stderr_of(completed)
    assert (tmp_path / "xdg" / __init__conf__.LAYEREDCONF_SLUG / "config.toml").is_file()


@_LINUX_ONLY
def test_a_real_broken_user_config_does_not_stop_info(broken_user_config_env: dict[str, str]) -> None:
    """End to end through the real loader: info does not read the configuration."""
    completed = subprocess.run(
        [sys.executable, "-m", "igittigitt", "info"],
        capture_output=True,
        check=False,
        env=broken_user_config_env,
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert completed.stdout


@_LINUX_ONLY
def test_a_real_broken_user_config_refuses_config_with_78(broken_user_config_env: dict[str, str]) -> None:
    """End to end through the real loader: config reads it, so it refuses and names the file."""
    completed = subprocess.run(
        [sys.executable, "-m", "igittigitt", "config"],
        capture_output=True,
        check=False,
        env=broken_user_config_env,
    )

    stderr = completed.stderr.decode("utf-8", "replace")
    assert completed.returncode == 78, stderr
    assert "config.toml is not valid TOML" in stderr
    assert "Traceback" not in stderr


@_LINUX_ONLY
def test_a_real_invalid_permission_section_is_replaced_by_a_forced_deploy(tmp_path: Path) -> None:
    """End to end: the command that replaces a bad file is not blocked by the value it replaces.

    The library never reads the files a deploy writes, so ``--force`` alone gets past the value.
    """
    config_dir = tmp_path / __init__conf__.LAYEREDCONF_SLUG
    config_dir.mkdir()
    bad = '[lib_layered_config.default_permissions]\nuser_directory = "0o777"\n'
    (config_dir / "config.toml").write_text(bad, encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "igittigitt",
            "config-deploy",
            "--target",
            "user",
            "--force",
        ],
        capture_output=True,
        check=False,
        env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path)},
    )

    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    assert (config_dir / "config.toml").read_text(encoding="utf-8") != bad
    assert stat.S_IMODE(config_dir.stat().st_mode) == 0o700


@_LINUX_ONLY
def test_a_real_invalid_profile_name_stops_info_with_a_usage_error(tmp_path: Path) -> None:
    """End to end through the real loader: an invalid --profile is not silently ignored."""
    completed = subprocess.run(
        [sys.executable, "-m", "igittigitt", "--profile", "../x", "info"],
        capture_output=True,
        check=False,
        env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path)},
    )

    assert completed.returncode == 2, completed.stderr.decode("utf-8", "replace")
