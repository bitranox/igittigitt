"""Permission settings loader for config deployment.

Provides functions to load permission defaults from configuration and
compute effective permission modes for deployment targets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lib_layered_config import (
    DEFAULT_APP_DIR_MODE,
    DEFAULT_APP_FILE_MODE,
    DEFAULT_USER_DIR_MODE,
    DEFAULT_USER_FILE_MODE,
)
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from lib_layered_config import Config

    from igittigitt.domain.enums import DeployTarget


class PermissionDefaults(BaseModel):
    """Validated, immutable permission defaults for deployment layers.

    Parsed at the boundary from ``[lib_layered_config.default_permissions]``
    config section. All fields have library-level fallback defaults.

    Example:
        >>> defaults = PermissionDefaults()
        >>> defaults.user_directory == 0o700
        True
    """

    model_config = ConfigDict(frozen=True)

    app_directory: int = DEFAULT_APP_DIR_MODE
    app_file: int = DEFAULT_APP_FILE_MODE
    host_directory: int = DEFAULT_APP_DIR_MODE
    host_file: int = DEFAULT_APP_FILE_MODE
    user_directory: int = DEFAULT_USER_DIR_MODE
    user_file: int = DEFAULT_USER_FILE_MODE
    enabled: bool = True

    def dir_mode_for(self, layer: str) -> int:
        """Return directory mode for the given layer name."""
        return getattr(self, f"{layer}_directory")

    def file_mode_for(self, layer: str) -> int:
        """Return file mode for the given layer name."""
        return getattr(self, f"{layer}_file")


def parse_mode(value: int | str, default: int) -> int:
    """Parse a permission mode value from config.

    Accepts either an integer or an octal string (e.g., "0o755" or "755").

    Args:
        value: Integer mode or octal string.
        default: Fallback value if parsing fails.

    Returns:
        Integer permission mode.

    Example:
        >>> parse_mode(493, 0o755)
        493
        >>> parse_mode("0o755", 0o644)
        493
        >>> parse_mode("755", 0o644)
        493
    """
    if isinstance(value, int):
        return value
    # value is str at this point
    try:
        # Handle both "755" and "0o755" formats
        if value.startswith("0o"):
            return int(value, 0)  # int() auto-detects 0o prefix
        return int(value, 8)  # Plain "755" needs explicit base 8
    except ValueError:
        return default


def _parse_mode_from_section(section: dict[str, int | str | bool], key: str, default: int) -> int:
    """Extract and parse a mode value from a raw config section dict.

    Used only at the boundary when parsing the raw config dict into
    PermissionDefaults. The raw section comes from lib_layered_config's
    Config.get() which returns untyped dicts.
    """
    raw = section.get(key, default)
    if isinstance(raw, bool):
        return default
    return parse_mode(raw, default)


def get_permission_defaults(config: Config) -> PermissionDefaults:
    """Load permission defaults from [lib_layered_config.default_permissions].

    Reads configurable permission defaults for each deployment layer.
    Falls back to lib_layered_config library defaults if not configured.

    Args:
        config: Configuration object with merged settings.

    Returns:
        PermissionDefaults model with typed fields for each layer's
        directory and file modes, plus an enabled flag.

    Example:
        >>> from lib_layered_config import Config
        >>> config = Config({}, {})  # Empty config
        >>> defaults = get_permission_defaults(config)
        >>> defaults.user_directory == 0o700
        True
    """
    section = config.get("lib_layered_config", {}).get("default_permissions", {})
    # NOTE: lib_layered_config does not define separate HOST_* constants.
    # Host layer shares defaults with app layer (both world-readable: 755/644).
    # This is intentional per CLAUDE.md "Deployment Permissions" documentation.
    return PermissionDefaults(
        app_directory=_parse_mode_from_section(section, "app_directory", DEFAULT_APP_DIR_MODE),
        app_file=_parse_mode_from_section(section, "app_file", DEFAULT_APP_FILE_MODE),
        host_directory=_parse_mode_from_section(section, "host_directory", DEFAULT_APP_DIR_MODE),
        host_file=_parse_mode_from_section(section, "host_file", DEFAULT_APP_FILE_MODE),
        user_directory=_parse_mode_from_section(section, "user_directory", DEFAULT_USER_DIR_MODE),
        user_file=_parse_mode_from_section(section, "user_file", DEFAULT_USER_FILE_MODE),
        enabled=section.get("enabled", True),
    )


def get_modes_for_target(
    target: DeployTarget,
    config: Config,
    *,
    dir_mode_override: int | None = None,
    file_mode_override: int | None = None,
) -> tuple[int, int]:
    """Get dir_mode and file_mode for a target, applying overrides.

    Retrieves permission modes for a deployment target from configuration,
    then applies any CLI overrides. CLI overrides take precedence over
    configured defaults.

    Args:
        target: The deployment target layer (app, host, or user).
        config: Configuration object with merged settings.
        dir_mode_override: CLI override for directory mode. If provided,
            takes precedence over configuration.
        file_mode_override: CLI override for file mode. If provided,
            takes precedence over configuration.

    Returns:
        Tuple of (dir_mode, file_mode) to pass to deploy_config.
        Values are integers (octal mode values). Always returns valid modes
        since get_permission_defaults provides fallbacks for all targets.

    Example:
        >>> from lib_layered_config import Config
        >>> from igittigitt.domain.enums import DeployTarget
        >>> config = Config({}, {})
        >>> dir_mode, file_mode = get_modes_for_target(
        ...     DeployTarget.USER, config
        ... )
        >>> dir_mode == 0o700
        True
    """
    defaults = get_permission_defaults(config)
    layer = target.value  # "app", "host", or "user"

    dir_mode: int = dir_mode_override if dir_mode_override is not None else defaults.dir_mode_for(layer)
    file_mode: int = file_mode_override if file_mode_override is not None else defaults.file_mode_for(layer)

    return dir_mode, file_mode


__all__ = [
    "PermissionDefaults",
    "get_modes_for_target",
    "get_permission_defaults",
    "parse_mode",
]
