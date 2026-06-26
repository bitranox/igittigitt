"""Performance knobs are configurable via lib_layered_config and take effect."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner

from igittigitt.adapters.cli import cli
from igittigitt.adapters.config.performance import PerformanceSettings, load_performance_settings

Factory = Callable[[], object]


@pytest.mark.os_agnostic
def test_performance_settings_defaults_are_evaluated_values() -> None:
    s = PerformanceSettings()
    assert s.dir_cache_max == 8192
    assert s.pattern_cache_max == 4096
    assert s.stdin_chunk_bytes == 65536
    assert s.max_token_bytes == 1 << 20


@pytest.mark.os_agnostic
def test_load_performance_settings_from_real_config() -> None:
    """The bundled defaultconfig.d/50-performance.toml provides the knobs."""
    from igittigitt.adapters.config.loader import get_config

    settings = load_performance_settings(get_config())
    assert settings.dir_cache_max == 8192
    assert settings.stdin_chunk_bytes == 65536


@pytest.mark.os_agnostic
def test_set_dir_cache_max_zero_keeps_correct_matching(
    cli_runner: CliRunner, production_factory: Factory, tmp_path: Path
) -> None:
    """Disabling the directory cache (knob=0) must not change the result."""
    (tmp_path / ".gitignore").write_text("build/\n!build/keep.log\n", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "keep.log").touch()
    result = cli_runner.invoke(
        cli,
        ["--set", "performance.dir_cache_max=0", "check", "-C", str(tmp_path), "build/keep.log"],
        obj=production_factory,
    )
    # build/ is excluded so keep.log under it stays ignored (parent pruning)
    assert "build/keep.log" in result.stdout


@pytest.mark.os_agnostic
def test_set_max_token_bytes_tightens_the_guard(
    cli_runner: CliRunner, production_factory: Factory, tmp_path: Path
) -> None:
    """Lowering max_token_bytes makes the separator-less guard trip sooner."""
    result = cli_runner.invoke(
        cli,
        ["--set", "performance.max_token_bytes=8", "filter", "-C", str(tmp_path)],
        input="aaaaaaaaaaaaaaaa",  # 16 bytes, no separator
        obj=production_factory,
    )
    assert result.exit_code != 0
    assert "exceeds 8 bytes" in result.output
