"""Deploy default configuration to app/host/user target directories."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lib_layered_config import deploy_config
from lib_layered_config.examples.deploy import DeployAction

from igittigitt import __init__conf__
from igittigitt.adapters.config.loader import get_default_config_path, validate_profile

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from igittigitt.domain.enums import DeployTarget

_DEPLOYED_ACTIONS = frozenset({DeployAction.CREATED, DeployAction.OVERWRITTEN})


def deploy_configuration(
    *,
    targets: Sequence[DeployTarget],
    force: bool = False,
    profile: str | None = None,
    set_permissions: bool | None = None,
    dir_mode: int | None = None,
    file_mode: int | None = None,
    permission_overrides: Mapping[str, object] | None = None,
) -> list[Path]:
    r"""Deploy default configuration to specified target layers.

    Users need to initialize configuration files in standard locations
    (application, host, or user config directories) without manually
    copying files or knowing platform-specific paths. Uses
    lib_layered_config.deploy_config() to copy the bundled defaultconfig.toml
    to requested target layers (app, host, user).

    Args:
        targets: Sequence of DeployTarget enum values specifying target layers.
            Valid values: DeployTarget.APP, DeployTarget.HOST, DeployTarget.USER.
            Multiple targets can be specified to deploy to several locations at once.
        force: If True, overwrite existing configuration files. If False (default),
            skip files that already exist.
        profile: Optional profile name for environment isolation. When specified,
            configuration is deployed to profile-specific subdirectories
            (e.g., ~/.config/slug/profile/<name>/config.toml).
        set_permissions: True sets Unix modes on the files and directories written, False
            leaves them to the umask, None (default) lets lib_layered_config follow the
            configured ``[lib_layered_config.default_permissions].enabled`` (on when unset).
            Each mode not given explicitly comes from that section for the target's layer,
            else the built-in one (755/644 for app/host, 700/600 for user). lib_layered_config
            reads the section itself, from the bundled defaults, the app, host and user files
            this call does not write, and the environment - never from ``.env``.
        dir_mode: Directory mode for every target (octal integer, e.g., 0o750), overriding
            the configured and built-in ones.
        file_mode: File mode for every target (octal integer, e.g., 0o640), overriding
            the configured and built-in ones.
        permission_overrides: Runtime values for keys of
            ``[lib_layered_config.default_permissions]`` by setting name
            (``{"user_file": "0o640"}``), laid over lib_layered_config's own read of the
            section and validated like configured values.

    Returns:
        List of paths where configuration files were created or would be created.
        Empty list if all target files already exist and force=False.

    Raises:
        PermissionError: When deploying to app/host without sufficient privileges.
        ValueError: When invalid target names are provided.
        DeployModeError: A mode is unsafe, or one was given with ``set_permissions=False``.
        DeployPermissionsError: The permission settings cannot be read or are invalid, or a
            ``permission_overrides`` value is refused; nothing has been written.

    Side Effects:
        Creates configuration files in platform-specific directories:
        - app: System-wide application config (requires privileges)
        - host: System-wide host config (requires privileges)
        - user: User-specific config (current user's home directory)

    Note:
        Platform-specific paths (without profile):
        - Linux (app): /etc/xdg/{slug}/config.toml
        - Linux (host): /etc/xdg/{slug}/hosts/{hostname}.toml
        - Linux (user): ~/.config/{slug}/config.toml
        - macOS (app): /Library/Application Support/{vendor}/{app}/config.toml
        - macOS (host): /Library/Application Support/{vendor}/{app}/hosts/{hostname}.toml
        - macOS (user): ~/Library/Application Support/{vendor}/{app}/config.toml
        - Windows (app): C:\ProgramData\{vendor}\{app}\config.toml
        - Windows (host): C:\ProgramData\{vendor}\{app}\hosts\{hostname}.toml
        - Windows (user): %APPDATA%\{vendor}\{app}\config.toml

        Platform-specific paths (with profile='production'):
        - Linux (user): ~/.config/{slug}/profile/production/config.toml
        - Linux (host): /etc/xdg/{slug}/profile/production/hosts/{hostname}.toml
        - etc.
    """
    if profile is not None:
        validate_profile(profile)
    source = get_default_config_path()

    # Convert enum values to strings for lib_layered_config
    target_strings = [t.value for t in targets]

    results = deploy_config(
        source=source,
        vendor=__init__conf__.LAYEREDCONF_VENDOR,
        app=__init__conf__.LAYEREDCONF_APP,
        slug=__init__conf__.LAYEREDCONF_SLUG,
        profile=profile,
        targets=target_strings,
        force=force,
        set_permissions=set_permissions,
        dir_mode=dir_mode,
        file_mode=file_mode,
        permission_overrides=permission_overrides,
    )

    # Extract paths where files were actually created or overwritten
    paths: list[Path] = []
    for result in results:
        if result.action in _DEPLOYED_ACTIONS:
            paths.append(result.destination)
        paths.extend(
            dot_d_result.destination
            for dot_d_result in result.dot_d_results
            if dot_d_result.action in _DEPLOYED_ACTIONS
        )
    return paths


__all__ = [
    "deploy_configuration",
]
