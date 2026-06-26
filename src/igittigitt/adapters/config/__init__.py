"""Configuration adapter - loading, deployment, display, and overrides.

Provides adapters for configuration management using lib_layered_config.

Contents:
    * :mod:`.loader` - Configuration loading with caching
    * :mod:`.deploy` - Configuration deployment to target locations
    * :mod:`.display` - Configuration display in human/JSON formats
    * :mod:`.overrides` - CLI ``--set`` override parsing and application
"""

from __future__ import annotations

from .deploy import deploy_configuration
from .display import display_config
from .loader import get_config, get_default_config_path
from .overrides import apply_overrides

__all__ = [
    "get_config",
    "get_default_config_path",
    "deploy_configuration",
    "display_config",
    "apply_overrides",
]
