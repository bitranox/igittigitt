"""display_config takes its output format as the plain value too."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest
from lib_layered_config import Config

from igittigitt.adapters.config.display import display_config

if TYPE_CHECKING:
    from igittigitt.domain.enums import OutputFormat


@pytest.mark.os_agnostic
def test_display_takes_the_format_as_its_plain_value(capsys: pytest.CaptureFixture[str]) -> None:
    """An untyped caller passing "json" gets JSON, as for OutputFormat.JSON, rather than an AttributeError."""
    config = Config({"section": {"key": "value"}}, {})
    display_config(config, output_format=cast("OutputFormat", "json"))
    assert json.loads(capsys.readouterr().out) == {"section": {"key": "value"}}
