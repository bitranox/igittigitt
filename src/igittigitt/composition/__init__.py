"""Composition root wiring adapters to application ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..adapters.config.deploy import deploy_configuration
from ..adapters.config.display import display_config

# Configuration services
from ..adapters.config.loader import get_config, get_default_config_path

# Logging services
from ..adapters.logging.setup import init_logging

# Static conformance assertions - pyright verifies that each adapter function
# structurally satisfies its corresponding Protocol at type-check time.
if TYPE_CHECKING:
    from ..application.ports import (
        DeployConfiguration,
        DisplayConfig,
        GetConfig,
        GetDefaultConfigPath,
        InitLogging,
    )

    _assert_get_config: GetConfig = get_config
    _assert_get_default_config_path: GetDefaultConfigPath = get_default_config_path
    _assert_deploy_configuration: DeployConfiguration = deploy_configuration
    _assert_display_config: DisplayConfig = display_config
    _assert_init_logging: InitLogging = init_logging


@dataclass(frozen=True, slots=True)
class AppServices:
    """Frozen container holding all application port implementations."""

    get_config: GetConfig
    get_default_config_path: GetDefaultConfigPath
    deploy_configuration: DeployConfiguration
    display_config: DisplayConfig
    init_logging: InitLogging


def build_production() -> AppServices:
    """Wire production adapters into an AppServices container."""
    return AppServices(
        get_config=get_config,
        get_default_config_path=get_default_config_path,
        deploy_configuration=deploy_configuration,
        display_config=display_config,
        init_logging=init_logging,
    )


def build_testing() -> AppServices:
    """Wire in-memory adapters into an AppServices container (no filesystem I/O)."""
    # Deferred: test-only in-memory adapters must not load in the production import graph.
    from ..adapters.memory import (  # noqa: PLC0415 - lazy load, test-only adapters
        deploy_configuration_in_memory,
        display_config_in_memory,
        get_config_in_memory,
        get_default_config_path_in_memory,
        init_logging_in_memory,
    )

    return AppServices(
        get_config=get_config_in_memory,
        get_default_config_path=get_default_config_path_in_memory,
        deploy_configuration=deploy_configuration_in_memory,
        display_config=display_config_in_memory,
        init_logging=init_logging_in_memory,
    )


__all__ = [
    # Composition
    "AppServices",
    "build_production",
    "build_testing",
    "deploy_configuration",
    "display_config",
    # Configuration
    "get_config",
    "get_default_config_path",
    # Logging
    "init_logging",
]
