"""Configuration display and deployment CLI commands.

Provides commands to inspect, deploy, and generate example configuration.

Contents:
    * :func:`cli_config` - Display merged configuration.
    * :func:`cli_config_deploy` - Deploy configuration to target locations.
    * :func:`cli_config_generate_examples` - Generate example configuration files.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Final, cast

import lib_log_rich.runtime
import rich_click as click
from lib_layered_config import (
    Config,
    DeployMode,
    DeployModeError,
    DeployPermissionsError,
    ModeKind,
    generate_examples,
)

from igittigitt import __init__conf__
from igittigitt.adapters.config.overrides import apply_overrides, nest_overrides
from igittigitt.domain.enums import DeployTarget, OutputFormat

from ..constants import CLICK_CONTEXT_SETTINGS
from ..context import CLIContext, get_cli_context
from ..exit_codes import ExitCode
from ..typed_click import option

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@click.command("config", context_settings=CLICK_CONTEXT_SETTINGS)
@option(
    "--format",
    "output_format",
    type=click.Choice([f.value for f in OutputFormat], case_sensitive=False),
    default=OutputFormat.HUMAN.value,
    help="Output format (human-readable or JSON)",
)
@option(
    "--section",
    type=str,
    default=None,
    help="Show only a specific configuration section (e.g., 'lib_log_rich')",
)
@option(
    "--profile",
    type=str,
    default=None,
    help="Override profile from root command (e.g., 'production', 'test')",
)
@click.pass_context
def cli_config(ctx: click.Context, output_format: str, section: str | None, profile: str | None) -> None:
    """Display the current merged configuration from all sources.

    Shows configuration loaded from defaults, application/user config files,
    .env files, and environment variables.

    Precedence: defaults -> app -> host -> user -> dotenv -> env

    Example:
        >>> from click.testing import CliRunner
        >>> from unittest.mock import MagicMock
        >>> runner = CliRunner()
        >>> # Real invocation tested in test_cli_config.py
    """
    cli_ctx = get_cli_context(ctx)
    effective_config, effective_profile = _resolve_config(cli_ctx, profile)
    fmt = OutputFormat(output_format.lower())

    extra = {"command": "config", "format": fmt.value, "profile": effective_profile}
    with lib_log_rich.runtime.bind(job_id="cli-config", extra=extra):
        logger.info(
            "Displaying configuration",
            extra={"format": fmt.value, "section": section, "profile": effective_profile},
        )
        click.echo()
        try:
            cli_ctx.services.display_config(
                effective_config, output_format=fmt, section=section, profile=effective_profile
            )
        except ValueError as exc:
            click.echo(f"\nError: {exc}", err=True)
            raise SystemExit(ExitCode.INVALID_ARGUMENT) from exc


def _get_effective_profile(cli_ctx: CLIContext, profile_override: str | None) -> str | None:
    """Get effective profile: override takes precedence over context."""
    return profile_override if profile_override else cli_ctx.profile


def _resolve_config(cli_ctx: CLIContext, profile: str | None) -> tuple[Config, str | None]:
    """Resolve configuration from context or reload with profile override.

    When a subcommand-level profile override is specified, reloads config
    with that profile and reapplies any root-level ``--set`` overrides
    stored in the CLI context.

    Args:
        cli_ctx: CLI context containing stored config and services.
        profile: Optional profile override.

    Returns:
        Tuple of (config, effective_profile).
    """
    effective_profile = _get_effective_profile(cli_ctx, profile)
    if profile:
        config = cli_ctx.services.get_config(profile=profile)
        return apply_overrides(config, cli_ctx.set_overrides), effective_profile
    return cli_ctx.config, effective_profile


def _parse_deploy_mode(value: str | None, *, kind: ModeKind) -> int | None:
    """Parse an octal mode string (``750`` or ``0o750``) and refuse an unsafe one.

    lib_layered_config's :class:`DeployMode` holds the one rule for a textual mode and for
    what is safe on configuration that can hold secrets, so this option and the library's
    own check can never disagree.

    Args:
        value: Octal mode string from the CLI, or None when the option was not given.
        kind: Whether the value is ``--dir-mode`` (a directory) or ``--file-mode`` (a file).

    Returns:
        The permission mode, or None if value was None.

    Raises:
        click.BadParameter: The value is not a plain octal literal, lies outside 0..0o7777,
            or is unsafe for configuration that can hold secrets.
    """
    if value is None:
        return None
    try:
        return DeployMode.from_text(value, kind).value
    except DeployModeError as exc:
        raise click.BadParameter(str(exc)) from exc


def _parse_dir_mode(_ctx: click.Context, _param: click.Parameter, value: str | None) -> int | None:
    """The ``--dir-mode`` callback; see :func:`_parse_deploy_mode`."""
    return _parse_deploy_mode(value, kind=ModeKind.DIRECTORY)


def _parse_file_mode(_ctx: click.Context, _param: click.Parameter, value: str | None) -> int | None:
    """The ``--file-mode`` callback; see :func:`_parse_deploy_mode`."""
    return _parse_deploy_mode(value, kind=ModeKind.FILE)


@click.command("config-deploy", context_settings=CLICK_CONTEXT_SETTINGS)
@option(
    "--target",
    "targets",
    type=click.Choice([t.value for t in DeployTarget], case_sensitive=False),
    multiple=True,
    required=True,
    help="Target configuration layer(s) to deploy to (can specify multiple)",
)
@option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing configuration files",
)
@option(
    "--profile",
    type=str,
    default=None,
    help="Override profile from root command (e.g., 'production', 'test')",
)
@option(
    "--permissions/--no-permissions",
    "set_permissions",
    default=None,
    help=(
        "Set Unix permissions (755/644 for app/host, 700/600 for user). "
        "Default: the configured enabled (on when unset)."
    ),
)
@option(
    "--dir-mode",
    type=str,
    default=None,
    callback=_parse_dir_mode,
    help="Override directory mode (octal, e.g., 750 or 0o750)",
)
@option(
    "--file-mode",
    type=str,
    default=None,
    callback=_parse_file_mode,
    help="Override file mode (octal, e.g., 640 or 0o640)",
)
@click.pass_context
def cli_config_deploy(
    ctx: click.Context,
    *,
    targets: tuple[str, ...],
    force: bool,
    profile: str | None,
    set_permissions: bool | None,
    dir_mode: int | None,
    file_mode: int | None,
) -> None:
    r"""Deploy default configuration to system or user directories.

    Creates configuration files in platform-specific locations:

    \b
    - app:  System-wide application config (requires privileges)
    - host: System-wide host config (requires privileges)
    - user: User-specific config (~/.config on Linux)

    By default, existing files are not overwritten. Use --force to overwrite.

    \b
    Permission options (POSIX only, no-op on Windows):
    - --permissions/--no-permissions: Enable/disable permission setting
    - --dir-mode: Override directory mode (octal, e.g., 750)
    - --file-mode: Override file mode (octal, e.g., 640)

    Without them, lib_layered_config decides the modes from
    [lib_layered_config.default_permissions] in the bundled defaults, the
    configuration files this deploy does not overwrite and the environment,
    with any --set of that section laid over them; never from .env.

    Example:
        >>> from click.testing import CliRunner
        >>> runner = CliRunner()
        >>> # Real invocation tested in test_cli_config.py
    """
    if set_permissions is False and (dir_mode is not None or file_mode is not None):
        raise click.UsageError(
            "--no-permissions cannot be combined with --dir-mode or --file-mode: "
            "a mode cannot be applied while permission setting is off"
        )
    cli_ctx = get_cli_context(ctx)
    effective_profile = _get_effective_profile(cli_ctx, profile)
    deploy_targets = tuple(DeployTarget(t.lower()) for t in targets)
    target_values = tuple(t.value for t in deploy_targets)

    extra = {"command": "config-deploy", "targets": target_values, "force": force, "profile": effective_profile}
    with lib_log_rich.runtime.bind(job_id="cli-config-deploy", extra=extra):
        _execute_deploy(
            cli_ctx,
            targets=deploy_targets,
            force=force,
            profile=effective_profile,
            set_permissions=set_permissions,
            dir_mode=dir_mode,
            file_mode=file_mode,
        )


def _execute_deploy(
    cli_ctx: CLIContext,
    *,
    targets: tuple[DeployTarget, ...],
    force: bool,
    profile: str | None,
    set_permissions: bool | None,
    dir_mode: int | None,
    file_mode: int | None,
) -> None:
    """Execute configuration deployment with error handling.

    The command decides no permission itself: what the command line said goes to
    lib_layered_config's ``deploy_config`` unchanged, and the library reads the configured
    settings without ``.env`` and without the files it overwrites, so neither can block or
    change a deploy.

    Args:
        cli_ctx: CLI context containing services.
        targets: Deployment target layers.
        force: Whether to overwrite existing files.
        profile: Optional profile name.
        set_permissions: ``--permissions`` (True), ``--no-permissions`` (False), or neither
            (None: the configured ``enabled`` decides).
        dir_mode: Directory mode for every target; None leaves it to the configured setting.
        file_mode: File mode for every target; None leaves it to the configured setting.

    Raises:
        SystemExit: On a refused permission setting (78), a permission error (13) or any
            other failure (1).
    """
    overrides = _permission_overrides(cli_ctx)
    try:
        deployed_paths = cli_ctx.services.deploy_configuration(
            targets=targets,
            force=force,
            profile=profile,
            set_permissions=set_permissions,
            dir_mode=dir_mode,
            file_mode=file_mode,
            permission_overrides=overrides,
        )
        # Logged after the call, so the line reports what happened rather than an attempt.
        logger.info(
            "Deployed configuration",
            extra={"targets": tuple(t.value for t in targets), "force": force, "profile": profile},
        )
        _report_deployment_result(deployed_paths, profile, set_permissions)
    except DeployPermissionsError as exc:
        _refuse_permission_settings(exc)
    except PermissionError as exc:
        logger.error("Permission denied when deploying configuration", extra={"error": str(exc)})
        click.echo(f"\nError: Permission denied. {exc}", err=True)
        click.echo("Hint: System-wide deployment (--target app/host) may require sudo.", err=True)
        raise SystemExit(ExitCode.PERMISSION_DENIED) from exc
    except Exception as exc:
        logger.error("Failed to deploy configuration", extra={"error": str(exc), "error_type": type(exc).__name__})
        click.echo(f"\nError: Failed to deploy configuration: {exc}", err=True)
        raise SystemExit(ExitCode.GENERAL_ERROR) from exc


_LAYERED_CONFIG_SECTION: Final[str] = "lib_layered_config"
_PERMISSIONS_KEY: Final[str] = "default_permissions"

#: How to deploy when the configured permission settings cannot be used. Both modes come
#: first: --no-permissions leaves every mode to the umask, which can make a user file that
#: holds a secret readable by other accounts.
_DEPLOY_ANYWAY_HINT: Final[str] = (
    "Hint: to deploy anyway, pass both --dir-mode and --file-mode (the built-in modes are 700 and 600 "
    "for user, 755 and 644 for app and host); --no-permissions also deploys, but leaves every mode to "
    "the umask, which can make a user file that holds secrets readable by other accounts."
)


def _permission_overrides(cli_ctx: CLIContext) -> Mapping[str, object] | None:
    """Return the ``--set lib_layered_config.default_permissions...`` values, keyed by setting name.

    Read from the same nested ``--set`` tree the ``config`` command lays over its output, so
    both commands see one value for one key (the last ``--set`` of a key wins in both), and a
    key such as ``default_permissions_x`` is never taken for the section. A deeper key
    (``...user_file.x=1``) arrives as a table value, which the library refuses by name.

    Args:
        cli_ctx: The state the root group stored; only its ``--set`` strings are read.

    Returns:
        The section's overrides, or None when no ``--set`` names the section.

    Raises:
        SystemExit: The section itself is set to a value that is not a table
            (``--set lib_layered_config.default_permissions=5`` or ``=null``); one stderr
            line names it, exit 78, nothing is deployed.
    """
    tree, _ = nest_overrides(cli_ctx.set_overrides)
    section = tree.get(_LAYERED_CONFIG_SECTION, {})
    if _PERMISSIONS_KEY not in section:
        return None
    value = section[_PERMISSIONS_KEY]
    if isinstance(value, Mapping):
        return cast("Mapping[str, object]", value)
    click.echo(
        f"Error: {_LAYERED_CONFIG_SECTION}.{_PERMISSIONS_KEY}: must be a table, "
        f"got {type(value).__name__} (source: override)",
        err=True,
    )
    raise SystemExit(ExitCode.CONFIG_ERROR)


def _refuse_permission_settings(exc: DeployPermissionsError) -> None:
    """Report lib_layered_config's refusal of the permission settings and exit 78.

    One ``Error:`` line per problem. The library's own hint names its Python parameters,
    so the CLI spelling replaces it. It is shown only when the library offers one: it does
    for a configured setting (both modes on the command line then deploy anyway), not for
    a refused ``--set``, which no mode option gets past.

    Raises:
        SystemExit: Always, with exit code 78.
    """
    logger.error("Refused permission settings", extra={"problems": [str(problem) for problem in exc.problems]})
    for problem in exc.problems:
        click.echo(f"Error: {problem}", err=True)
    if exc.hint is not None:
        click.echo(_DEPLOY_ANYWAY_HINT, err=True)
    raise SystemExit(ExitCode.CONFIG_ERROR) from exc


def _report_deployment_result(deployed_paths: list[Path], profile: str | None, set_permissions: bool | None) -> None:
    """Report deployment results to the user.

    Args:
        deployed_paths: List of paths where configs were deployed.
        profile: Optional profile name for display.
        set_permissions: What the command line said: False for ``--no-permissions``. None
            means the configured ``enabled`` decided, which this command does not read, so
            the report claims nothing about it.
    """
    if deployed_paths:
        profile_msg = f" (profile: {profile})" if profile else ""
        perm_msg = " (permissions not set)" if set_permissions is False else ""
        click.echo(f"\nConfiguration deployed successfully{profile_msg}{perm_msg}:")
        for path in deployed_paths:
            # ASCII marker on purpose: a non-ASCII glyph here crashes config-deploy with a
            # UnicodeEncodeError on a legacy Windows console codepage (cp1252) even though the
            # files were already written, so exit 1 misreports a deploy that actually succeeded.
            click.echo(f"  + {path}")
    else:
        click.echo("\nNo files were created (all target files already exist).")
        click.echo("Use --force to overwrite existing configuration files.")


@click.command("config-generate-examples", context_settings=CLICK_CONTEXT_SETTINGS)
@option("--destination", type=click.Path(file_okay=False), required=True, help="Directory to write example files")
@option("--force", is_flag=True, default=False, help="Overwrite existing files")
@click.pass_context
def cli_config_generate_examples(ctx: click.Context, destination: str, force: bool) -> None:
    """Generate example configuration files in a target directory.

    Creates example TOML configuration files showing all available options
    with their default values and documentation comments. Useful for learning
    the configuration structure, creating initial configuration files, or
    documenting available settings.

    By default, existing files are not overwritten. Use --force to overwrite.

    Example:
        >>> from click.testing import CliRunner
        >>> runner = CliRunner()
        >>> # Real invocation tested in test_cli_config.py
    """
    extra = {"command": "config-generate-examples", "destination": destination, "force": force}
    with lib_log_rich.runtime.bind(job_id="cli-config-generate-examples", extra=extra):
        logger.info("Generating example configuration files", extra={"destination": destination, "force": force})
        try:
            paths = generate_examples(
                destination=destination,
                slug=__init__conf__.LAYEREDCONF_SLUG,
                vendor=__init__conf__.LAYEREDCONF_VENDOR,
                app=__init__conf__.LAYEREDCONF_APP,
                force=force,
            )
            if paths:
                click.echo(f"\nGenerated {len(paths)} example file(s):")
                for p in paths:
                    click.echo(f"  {p}")
            else:
                click.echo("\nNo files generated (all already exist). Use --force to overwrite.")
        except Exception as exc:
            logger.error("Failed to generate examples", extra={"error": str(exc)})
            click.echo(f"\nError: {exc}", err=True)
            raise SystemExit(ExitCode.GENERAL_ERROR) from exc


__all__ = ["cli_config", "cli_config_deploy", "cli_config_generate_examples"]
