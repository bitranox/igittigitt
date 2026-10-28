"""Coerced .env values reach the logging settings as the operator meant them.

lib_layered_config's dotenv and environment layers turn an unquoted value into an int whenever
that number reads back as the same text (``4711`` stays ``4711``). The logging model's text fields
must therefore accept such a number, otherwise startup fails on an ordinary ``.env`` line. The
same layers turn ``null`` into None, which leaves a setting at its default, except for
``environment``, which refuses it.

These tests load a real ``.env`` through the real loader, so a change in the library's coercion
shows up here rather than on a deployment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from lib_log_rich.runtime import RuntimeConfig
from pydantic import ValidationError

from igittigitt import __init__conf__
from igittigitt.adapters.config.loader import get_config
from igittigitt.adapters.logging.setup import (
    LoggingConfigModel,
    _build_runtime_config,  # pyright: ignore[reportPrivateUsage]
)

if TYPE_CHECKING:
    from pathlib import Path

    from lib_layered_config import Config


def _load_dotenv(tmp_path: Path, line: str) -> Config:
    dotenv = tmp_path / ".env"
    dotenv.write_text(f"{line}\n", encoding="utf-8")
    return get_config(dotenv_path=str(dotenv))


@pytest.mark.os_agnostic
@pytest.mark.parametrize(
    ("env_key", "attr"),
    [("LIB_LOG_RICH__SERVICE", "service"), ("LIB_LOG_RICH__ENVIRONMENT", "environment")],
)
def test_digit_only_dotenv_value_reaches_the_runtime_config_as_its_text(
    tmp_path: Path, clear_config_cache: None, env_key: str, attr: str
) -> None:
    config = _load_dotenv(tmp_path, f"{env_key}=4711")
    # Premise: the library hands the value over as a number. Without it the test proves nothing.
    assert isinstance(config.get("lib_log_rich", {})[attr], int)

    runtime = _build_runtime_config(config)

    assert getattr(runtime, attr) == "4711"


@pytest.mark.os_agnostic
def test_a_non_scalar_service_is_still_refused() -> None:
    with pytest.raises(ValidationError):
        LoggingConfigModel.model_validate({"service": ["a"]})


@pytest.mark.os_agnostic
def test_a_null_dotenv_value_leaves_the_setting_at_lib_log_rich_s_default(
    tmp_path: Path, clear_config_cache: None
) -> None:
    config = _load_dotenv(tmp_path, "LIB_LOG_RICH__QUEUE_PUT_TIMEOUT=null")
    # Premise: the library hands the value over as None. Without it the test proves nothing.
    assert config.get("lib_log_rich", {})["queue_put_timeout"] is None

    runtime = _build_runtime_config(config)

    assert runtime.queue_put_timeout == RuntimeConfig.model_fields["queue_put_timeout"].default
    assert runtime.queue_put_timeout is not None


@pytest.mark.os_agnostic
def test_a_null_dotenv_environment_is_refused(tmp_path: Path, clear_config_cache: None) -> None:
    config = _load_dotenv(tmp_path, "LIB_LOG_RICH__ENVIRONMENT=null")

    with pytest.raises(ValidationError) as caught:
        _build_runtime_config(config)

    assert [error["loc"] for error in caught.value.errors()] == [("environment",)]


@pytest.mark.os_agnostic
@pytest.mark.parametrize("line", ["LIB_LOG_RICH__SERVICE=", "LIB_LOG_RICH__SERVICE=null"])
def test_an_empty_or_null_dotenv_service_names_the_package(tmp_path: Path, clear_config_cache: None, line: str) -> None:
    runtime = _build_runtime_config(_load_dotenv(tmp_path, line))

    assert runtime.service == __init__conf__.name


@pytest.mark.os_agnostic
def test_an_unknown_key_is_refused_by_name() -> None:
    # lib_log_rich 8 refuses a key RuntimeConfig does not define, so a misspelled setting is
    # reported instead of leaving the intended value at its default.
    with pytest.raises(ValidationError) as caught:
        LoggingConfigModel.model_validate({"console_levle": "DEBUG"})

    assert [(error["loc"], error["type"]) for error in caught.value.errors()] == [
        (("console_levle",), "extra_forbidden")
    ]
