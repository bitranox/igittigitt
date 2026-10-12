"""Digit-only .env values reach the logging settings as the text the operator wrote.

lib_layered_config's dotenv and environment layers turn an unquoted value into an int whenever
that number reads back as the same text (``4711`` stays ``4711``). The logging model's text fields
must therefore accept such a number, otherwise startup fails on an ordinary ``.env`` line.

These tests load a real ``.env`` through the real loader, so a change in the library's coercion
shows up here rather than on a deployment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

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
