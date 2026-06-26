"""Performance tuning knobs, loaded from the layered ``[performance]`` config.

These values only affect speed and cache memory, never which paths match (git
compatibility is unaffected). Defaults mirror ``defaultconfig.d/50-performance.toml``
and were chosen by measurement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from igittigitt.igittigitt import set_pattern_cache_size

if TYPE_CHECKING:
    from lib_layered_config import Config


class PerformanceSettings(BaseModel):
    """Validated ``[performance]`` knobs (see the config file for documentation)."""

    model_config = ConfigDict(extra="ignore")

    #: directory-decision LRU capacity (0 disables it)
    dir_cache_max: int = Field(default=8192, ge=0)
    #: compiled-regex cache capacity (process-wide)
    pattern_cache_max: int = Field(default=4096, ge=0)
    #: stdin read size in bytes for the streaming commands
    stdin_chunk_bytes: int = Field(default=65536, gt=0)
    #: per-token safety bound in bytes (guards the bounded-memory promise)
    max_token_bytes: int = Field(default=1 << 20, gt=0)


def load_performance_settings(config: Config) -> PerformanceSettings:
    """Build :class:`PerformanceSettings` from the ``[performance]`` config section."""
    raw = config.get("performance", default={})
    if not isinstance(raw, dict):
        raw = {}
    return PerformanceSettings.model_validate(raw)


def apply_process_wide(settings: PerformanceSettings) -> None:
    """Apply the knobs that are process-wide (currently the pattern cache size)."""
    set_pattern_cache_size(settings.pattern_cache_max)


__all__ = ["PerformanceSettings", "apply_process_wide", "load_performance_settings"]
