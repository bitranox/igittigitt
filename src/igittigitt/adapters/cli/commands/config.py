"""Configuration display and deployment CLI commands.

Provides commands to inspect, deploy, and generate example configuration.

Contents:
    * :func:`cli_config` - Display merged configuration.
    * :func:`cli_config_deploy` - Deploy configuration to target locations.
    * :func:`cli_config_generate_examples` - Generate example configuration files.
"""

from __future__ import annotations

import logging
from pathlib import Path

import lib_log_rich.runtime
import rich_click as click
from lib_layered_config import Config, generate_examples

from igittigitt import __init__conf__
from igittigitt.adapters.config.overrides import apply_overrides
from igittigitt.adapters.config.permissions import get_permission_defaults
from igittigitt.domain.enums import DeployTarget, OutputFormat

from ..constants import CLICK_CONTEXT_SETTINGS
from ..context import CLIContext, get_cli_context
from ..exit_codes import ExitCode
from ..typed_click import option

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


def _parse_octal_mode(ctx: click.Context, param: click.Parameter, value: str | None) -> int | None:
    """Parse octal mode string (e.g., '750' or '0o750') to int.

    Args:
        ctx: Click context (unused but required by callback signature).
        param: Click parameter (unused but required by callback signature).
        value: Octal mode string from CLI, or None.

    Returns:
        Integer permission mode, or None if value was None.

    Raises:
        click.BadParameter: If value cannot be parsed as octal.
    """
    if value is None:
        return None
    try:
        # Handle both '750' and '0o750' formats
        return int(value, 8) if not value.startswith("0o") else int(value, 0)
    except ValueError as exc:
        raise click.BadParameter(f"Invalid octal mode: {value}") from exc


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
    help="Set Unix permissions (755/644 for app/host, 700/600 for user). Default: enabled.",
)
@option(
    "--dir-mode",
    type=str,
    default=None,
    callback=_parse_octal_mode,
    help="Override directory mode (octal, e.g., 750 or 0o750)",
)
@option(
    "--file-mode",
    type=str,
    default=None,
    callback=_parse_octal_mode,
    help="Override file mode (octal, e.g., 640 or 0o640)",
)
@click.pass_context
def cli_config_deploy(
    ctx: click.Context,
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

    Example:
        >>> from click.testing import CliRunner
        >>> runner = CliRunner()
        >>> # Real invocation tested in test_cli_config.py
    """
    cli_ctx = get_cli_context(ctx)
    effective_profile = _get_effective_profile(cli_ctx, profile)
    deploy_targets = tuple(DeployTarget(t.lower()) for t in targets)
    target_values = tuple(t.value for t in deploy_targets)

    extra = {"command": "config-deploy", "targets": target_values, "force": force, "profile": effective_profile}
    with lib_log_rich.runtime.bind(job_id="cli-config-deploy", extra=extra):
        logger.info(
            "Deploying configuration",
            extra={"targets": target_values, "force": force, "profile": effective_profile},
        )
        _execute_deploy(cli_ctx, deploy_targets, force, effective_profile, set_permissions, dir_mode, file_mode)


def _execute_deploy(
    cli_ctx: CLIContext,
    targets: tuple[DeployTarget, ...],
    force: bool,
    profile: str | None,
    set_permissions: bool | None,
    dir_mode: int | None,
    file_mode: int | None,
) -> None:
    """Execute configuration deployment with error handling.

    Args:
        cli_ctx: CLI context containing services.
        targets: Deployment target layers.
        force: Whether to overwrite existing files.
        profile: Optional profile name.
        set_permissions: Whether to set Unix permissions. None uses config default.
        dir_mode: Override directory permission mode.
        file_mode: Override file permission mode.

    Raises:
        SystemExit: On permission or other errors.
    """
    # Get permission defaults from config
    perm_defaults = get_permission_defaults(cli_ctx.config)

    # CLI --permissions/--no-permissions overrides config enabled setting
    effective_set_permissions = set_permissions if set_permissions is not None else perm_defaults.enabled

    try:
        deployed_paths = cli_ctx.services.deploy_configuration(
            targets=targets,
            force=force,
            profile=profile,
            set_permissions=effective_set_permissions,
            dir_mode=dir_mode,
            file_mode=file_mode,
        )
        _report_deployment_result(deployed_paths, profile, effective_set_permissions)
    except PermissionError as exc:
        logger.error("Permission denied when deploying configuration", extra={"error": str(exc)})
        click.echo(f"\nError: Permission denied. {exc}", err=True)
        click.echo("Hint: System-wide deployment (--target app/host) may require sudo.", err=True)
        raise SystemExit(ExitCode.PERMISSION_DENIED) from exc
    except Exception as exc:
        logger.error("Failed to deploy configuration", extra={"error": str(exc), "error_type": type(exc).__name__})
        click.echo(f"\nError: Failed to deploy configuration: {exc}", err=True)
        raise SystemExit(ExitCode.GENERAL_ERROR) from exc


def _report_deployment_result(deployed_paths: list[Path], profile: str | None, set_permissions: bool) -> None:
    """Report deployment results to the user.

    Args:
        deployed_paths: List of paths where configs were deployed.
        profile: Optional profile name for display.
        set_permissions: Whether permissions were set.
    """
    if deployed_paths:
        profile_msg = f" (profile: {profile})" if profile else ""
        perm_msg = "" if set_permissions else " (permissions not set)"
        click.echo(f"\nConfiguration deployed successfully{profile_msg}{perm_msg}:")
        for path in deployed_paths:
            click.echo(f"  ✓ {path}")
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
