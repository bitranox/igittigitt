"""In-memory adapter implementations for testing.

Provides lightweight implementations of the config and logging ports that
operate entirely in memory - no filesystem, no logging framework.

Contents:
    * :mod:`.config` - In-memory configuration adapters
    * :mod:`.logging` - In-memory logging adapter
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import (
    deploy_configuration_in_memory,
    display_config_in_memory,
    get_config_in_memory,
    get_default_config_path_in_memory,
)
from .logging import init_logging_in_memory

# Static conformance assertions
if TYPE_CHECKING:
    from igittigitt.application.ports import (
        GetConfig,
        GetDefaultConfigPath,
        InitLogging,
    )

    _assert_get_config: GetConfig = get_config_in_memory
    _assert_get_default_config_path: GetDefaultConfigPath = get_default_config_path_in_memory
    _assert_init_logging: InitLogging = init_logging_in_memory

__all__ = [
    "deploy_configuration_in_memory",
    "display_config_in_memory",
    "get_config_in_memory",
    "get_default_config_path_in_memory",
    "init_logging_in_memory",
]
