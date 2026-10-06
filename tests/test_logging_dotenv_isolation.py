"""What the logging setup takes from a ``.env``, and what an invalid logging section does.

Logging reads lib_log_rich's own ``LOG_*`` variables from a ``.env``. Nothing else in that file may
reach the process environment: a later configuration load (``config --profile``, the deploy's
permission read) would take an app-prefixed line for the environment layer. With ``--env-file``,
that file is the only ``.env`` read. An invalid ``[lib_log_rich]`` section is a configuration
failure like a broken file: the commands that read the configuration refuse with exit 78, the
others still run.

The end-to-end tests run the real CLI in a subprocess with every configuration location under
``tmp_path``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import lib_log_rich.runtime
import pytest
from lib_layered_config import Config

from igittigitt import __init__conf__
from igittigitt.adapters.logging.setup import init_logging

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

PREFIX = __init__conf__.LAYEREDCONF_SLUG.upper().replace("-", "_")
_HOMES = ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "APPDATA", "LOCALAPPDATA")


def _run(cwd: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith((PREFIX, "LOG_", "LIB_LAYERED_CONFIG"))}
    clean.update(dict.fromkeys(_HOMES, str(cwd)))
    clean.update(env or {})
    return subprocess.run(
        [sys.executable, "-m", "igittigitt", *args],
        cwd=cwd,
        env=clean,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@pytest.fixture
def log_variables() -> Iterator[list[str]]:
    """Names a test lets ``init_logging`` set; each is removed from the environment afterwards."""
    names: list[str] = []
    yield names
    for name in names:
        os.environ.pop(name, None)


# ------------------------------------------------------------------ only LOG_* reaches the environment


@pytest.mark.os_agnostic
def test_only_log_variables_from_the_dotenv_reach_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_variables: list[str]
) -> None:
    app_key = f"{PREFIX}___PERFORMANCE__DIR_CACHE_MAX"
    log_variables.extend(["LOG_DOTENV_PROBE", app_key])
    (tmp_path / ".env").write_text(f"{app_key}=4321\nLOG_DOTENV_PROBE=from-dotenv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(app_key, raising=False)

    init_logging(Config({}, {}))

    assert os.environ.get("LOG_DOTENV_PROBE") == "from-dotenv"
    assert app_key not in os.environ


@pytest.mark.os_agnostic
def test_an_explicit_env_file_is_the_only_dotenv_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_variables: list[str]
) -> None:
    log_variables.extend(["LOG_FROM_CWD", "LOG_FROM_EXPLICIT"])
    (tmp_path / ".env").write_text("LOG_FROM_CWD=cwd\n", encoding="utf-8")
    explicit = tmp_path / "explicit.env"
    explicit.write_text("LOG_FROM_EXPLICIT=explicit\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    init_logging(Config({}, {}), dotenv_path=str(explicit))

    assert os.environ.get("LOG_FROM_EXPLICIT") == "explicit"
    assert "LOG_FROM_CWD" not in os.environ


@pytest.mark.os_agnostic
def test_a_dotenv_never_replaces_a_variable_already_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_variables: list[str]
) -> None:
    log_variables.append("LOG_ALREADY_SET")
    monkeypatch.setenv("LOG_ALREADY_SET", "from-environment")
    (tmp_path / ".env").write_text("LOG_ALREADY_SET=from-dotenv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    init_logging(Config({}, {}))

    assert os.environ["LOG_ALREADY_SET"] == "from-environment"


@pytest.mark.os_agnostic
def test_a_dotenv_that_is_not_utf8_does_not_stop_logging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, log_variables: list[str]
) -> None:
    """The loader already reports such a file as a configuration failure; logging must still start."""
    log_variables.append("LOG_AFTER_BAD_BYTES")
    (tmp_path / ".env").write_bytes(b"LOG_AFTER_BAD_BYTES=x\nNAME=\xff\xfe\n")
    monkeypatch.chdir(tmp_path)

    init_logging(Config({}, {}))

    assert lib_log_rich.runtime.is_initialised()


# ------------------------------------------------------------------ end to end: a .env cannot reach a reload


@pytest.mark.os_agnostic
def test_a_prefixed_line_in_the_cwd_dotenv_does_not_reach_a_profile_reload(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(f"{PREFIX}___PERFORMANCE__DIR_CACHE_MAX=4321\n", encoding="utf-8")

    result = _run(tmp_path, "config", "--profile", "production", "--format", "json", "--section", "performance")

    assert result.returncode == 0, result.stderr
    assert "dir_cache_max" in result.stdout  # liveness: the section is shown
    assert "4321" not in result.stdout


@pytest.mark.os_agnostic
def test_a_prefixed_permission_line_in_the_cwd_dotenv_does_not_block_a_deploy(tmp_path: Path) -> None:
    key = f"{PREFIX}___LIB_LAYERED_CONFIG__DEFAULT_PERMISSIONS__USER_FILE"
    (tmp_path / ".env").write_text(f"{key}=400\n", encoding="utf-8")

    result = _run(tmp_path, "config-deploy", "--target", "user", "--force")

    assert result.returncode == 0, result.stderr


# ------------------------------------------------------------------ an invalid [lib_log_rich] section


@pytest.mark.os_agnostic
def test_an_invalid_logging_section_leaves_commands_that_do_not_read_the_config_running(tmp_path: Path) -> None:
    result = _run(tmp_path, "info", env={f"{PREFIX}___LIB_LOG_RICH__RATE_LIMIT": "100:60"})

    assert result.returncode == 0, result.stderr
    assert f"Info for {__init__conf__.name}:" in result.stdout


@pytest.mark.os_agnostic
def test_an_invalid_logging_section_is_a_configuration_error_naming_the_key(tmp_path: Path) -> None:
    result = _run(tmp_path, "config", env={f"{PREFIX}___LIB_LOG_RICH__RATE_LIMIT": "100:60"})

    assert result.returncode == 78
    errors = [line for line in result.stderr.splitlines() if line.startswith("Error:")]
    assert len(errors) == 1, result.stderr
    assert "lib_log_rich.rate_limit" in errors[0]
    assert "pydantic.dev" not in result.stderr
    assert "100:60" not in result.stderr


@pytest.mark.os_agnostic
def test_each_refused_logging_setting_gets_its_own_line(tmp_path: Path) -> None:
    env = {f"{PREFIX}___LIB_LOG_RICH__RATE_LIMIT": "100:60", f"{PREFIX}___LIB_LOG_RICH__RING_BUFFER_SIZE": "abc"}

    result = _run(tmp_path, "config", env=env)

    errors = [line for line in result.stderr.splitlines() if line.startswith("Error:")]
    assert result.returncode == 78
    assert sorted(e.split(":", 2)[1].strip() for e in errors) == [
        "lib_log_rich.rate_limit",
        "lib_log_rich.ring_buffer_size",
    ]


@pytest.mark.os_agnostic
def test_a_value_only_lib_log_rich_itself_refuses_is_a_configuration_error_too(tmp_path: Path) -> None:
    """``queue_maxsize = 0`` passes the type check and is refused by lib_log_rich's own range check."""
    env = {f"{PREFIX}___LIB_LOG_RICH__QUEUE_MAXSIZE": "0"}

    refused = _run(tmp_path, "config", env=env)
    running = _run(tmp_path, "info", env=env)

    assert refused.returncode == 78
    assert "lib_log_rich.queue_maxsize" in refused.stderr
    assert "pydantic.dev" not in refused.stderr
    assert running.returncode == 0, running.stderr


@pytest.mark.os_agnostic
def test_an_invalid_logging_section_does_not_block_the_deploy_that_replaces_it(tmp_path: Path) -> None:
    result = _run(
        tmp_path, "config-deploy", "--target", "user", "--force", env={f"{PREFIX}___LIB_LOG_RICH__RATE_LIMIT": "100:60"}
    )

    assert result.returncode == 0, result.stderr
