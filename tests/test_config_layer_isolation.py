"""The suite never reads the app or host configuration layer of the machine it runs on.

A host with the CLI deployed system-wide (``/etc/xdg/<slug>/`` on Linux, ``/Library/Application
Support/<vendor>/<app>/`` on macOS, ``C:\\ProgramData\\<vendor>\\<app>\\`` on Windows) would
otherwise decide test results: a ``config.d/99-*.toml`` setting a value there makes tests fail on
that machine while a clean CI runner stays green. These tests ask lib_layered_config where those
layers live, with the code its deploy and its reader share, rather than inspecting the
environment variables the conftest sets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from lib_layered_config import deploy_config_paths

from igittigitt import __init__conf__
from igittigitt.adapters.config.loader import get_config, get_default_config_path

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.os_agnostic
@pytest.mark.parametrize("target", ["app", "host"])
def test_the_system_config_layers_resolve_inside_the_test_s_own_directory(target: str, tmp_path: Path) -> None:
    paths = deploy_config_paths(
        get_default_config_path(),
        vendor=__init__conf__.LAYEREDCONF_VENDOR,
        app=__init__conf__.LAYEREDCONF_APP,
        slug=__init__conf__.LAYEREDCONF_SLUG,
        targets=[target],
    )
    outside = sorted(path for path in paths if not path.is_relative_to(tmp_path.resolve()))

    assert outside == [], f"the {target} layer resolves outside this test's directory: {outside}"


@pytest.mark.os_agnostic
def test_a_file_in_the_redirected_app_layer_is_what_the_loader_reads(
    app_layer_config_file: Path, clear_config_cache: None
) -> None:
    app_layer_config_file.write_text('[layer_isolation_probe]\nread_from = "redirected app layer"\n', encoding="utf-8")

    config = get_config()

    assert config.get("layer_isolation_probe.read_from") == "redirected app layer"
