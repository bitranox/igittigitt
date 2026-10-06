"""Centralized logging initialization for all entry points.

Provides a single source of truth for lib_log_rich runtime configuration,
eliminating duplication between module entry (__main__.py) and console script
(cli.py) while ensuring initialization happens exactly once.

Contents:
    * :func:`init_logging` - idempotent logging initialization with layered config.
    * :class:`InvalidLoggingConfigError` - the ``[lib_log_rich]`` section cannot configure logging.
    * :func:`_build_runtime_config` - constructs RuntimeConfig from layered sources.

System Role:
    Lives in the adapters/platform layer. All entry points (module execution,
    console scripts, tests) delegate to this module for logging setup, ensuring
    consistent runtime behavior across invocation paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

import lib_log_rich.runtime
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, ValidationError

from igittigitt import __init__conf__

if TYPE_CHECKING:
    from lib_layered_config import Config


class LoggingConfigModel(BaseModel):
    """Pydantic model for [lib_log_rich] config section validation.

    Used at the boundary to parse configuration dictionaries into typed fields.
    Extra fields are allowed to pass through to lib_log_rich.RuntimeConfig.

    Example:
        >>> model = LoggingConfigModel(service="myapp", environment="staging")
        >>> model.service
        'myapp'
        >>> model.environment
        'staging'

        >>> default = LoggingConfigModel()
        >>> default.environment
        'prod'
    """

    service: str | None = None
    environment: str = "prod"

    model_config = ConfigDict(extra="allow")


def _build_runtime_config(config: Config) -> lib_log_rich.runtime.RuntimeConfig:
    """Build RuntimeConfig from a Config object.

    Centralizes the mapping from lib_layered_config to lib_log_rich
    RuntimeConfig. Uses Pydantic for single-parse validation at the boundary.

    Args:
        config: Already-loaded layered configuration object.

    Returns:
        Fully configured runtime settings ready for lib_log_rich.init().

    Note:
        Configuration is read from the [lib_log_rich] section. All parameters
        documented in defaultconfig.toml can be specified. Unspecified values
        use lib_log_rich's built-in defaults. The service and environment
        parameters default to package metadata when not configured.
    """
    log_raw: object = config.get("lib_log_rich", default={})
    parsed = LoggingConfigModel.model_validate(cast("dict[str, object]", log_raw) if log_raw else {})

    # Apply defaults for required fields
    service = parsed.service or __init__conf__.name
    environment = parsed.environment

    # Get extra fields passed through by Pydantic
    extra_config = parsed.model_dump(exclude={"service", "environment"}, exclude_none=True)

    return lib_log_rich.runtime.RuntimeConfig(
        service=service,
        environment=environment,
        **extra_config,
    )


class InvalidLoggingConfigError(Exception):
    """lib_log_rich refuses its settings: one ``<key>: <reason>`` in :attr:`problems` per problem.

    The settings are the ``[lib_log_rich]`` section plus any ``LOG_*`` variable. A problem names
    the key and never repeats the refused value.

    Attributes:
        problems: One line per refused setting.

    Example:
        >>> from lib_layered_config import Config
        >>> try:
        ...     init_logging(Config({"lib_log_rich": {"rate_limit": "100:60"}}, {}))
        ... except InvalidLoggingConfigError as exc:
        ...     print(exc)
        lib_log_rich.rate_limit: Input should be a valid tuple
    """

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


#: The variables lib_log_rich reads itself; the only lines of a ``.env`` logging takes.
_LOG_VARIABLE_PREFIX = "LOG_"
#: A directory holding one of these is a project root: the upward ``.env`` search stops there.
_PROJECT_MARKERS = ("pyproject.toml", ".git")


def _problems(error: BaseException) -> list[str]:
    """One line per problem, from the first pydantic error in ``error``'s chain; never the value."""
    cause: BaseException | None = error
    while cause is not None and not isinstance(cause, ValidationError):
        cause = cause.__cause__ or cause.__context__
    if cause is None:
        # Not a pydantic error (e.g. an unknown level name): its own first line, which names
        # the setting.
        return [f"lib_log_rich: {str(error).splitlines()[0]}"]
    return [f"lib_log_rich.{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in cause.errors()]


def _nearest_dotenv() -> Path | None:
    """The ``.env`` in the working directory or the nearest parent, up to the project root.

    Walks by path only: no ``chdir``, and a directory that cannot be read is passed over.
    """
    try:
        start = Path.cwd()
    except OSError:
        return None
    for directory in (start, *start.parents):
        found, stop = _dotenv_in(directory)
        if found is not None or stop:
            return found
    return None


def _dotenv_in(directory: Path) -> tuple[Path | None, bool]:
    """The ``.env`` in ``directory``, and whether the search stops there (a project root).

    A directory that cannot be read is passed over: Python before 3.14 raises for a path
    behind a directory without search permission instead of answering False.
    """
    try:
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate, True
        return None, any((directory / marker).exists() for marker in _PROJECT_MARKERS)
    except OSError:
        return None, False


def _load_log_variables(dotenv_path: str | None) -> None:
    """Copy the ``LOG_*`` lines of a ``.env`` into the environment, never replacing a set variable.

    Only ``LOG_*``: any other line would be read as the environment layer by a later
    configuration load (``config --profile``, the deploy's permission read). A file that
    cannot be read or decoded is skipped; the configuration loader reports it.
    """
    path = Path(dotenv_path) if dotenv_path is not None else _nearest_dotenv()
    if path is None:
        return
    try:
        values = dotenv_values(path, encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    for name, value in values.items():
        if name.startswith(_LOG_VARIABLE_PREFIX) and value is not None:
            os.environ.setdefault(name, value)


def init_logging(config: Config, *, dotenv_path: str | None = None) -> None:
    """Initialize lib_log_rich runtime with the provided configuration.

    All entry points need logging configured, but the runtime should only
    be initialized once regardless of how many times this function is called.
    Loads .env files (to make LOG_* variables available), checks if lib_log_rich
    is already initialized, and configures it with settings from the provided
    Config object. Bridges standard Python logging to lib_log_rich for domain
    code compatibility.

    Args:
        config: Already-loaded layered configuration object containing logging
            settings in the [lib_log_rich] section.
        dotenv_path: The ``.env`` the configuration was loaded with (``--env-file``), or None
            to use the nearest ``.env`` from the working directory up to the project root.

    Raises:
        InvalidLoggingConfigError: The ``[lib_log_rich]`` section holds a value lib_log_rich
            refuses; logging is not started.

    Side Effects:
        Copies the ``LOG_*`` lines of that ``.env`` into the process environment on first
        invocation; no other line, and no variable that is already set.
        May initialize the global lib_log_rich runtime on first invocation.
        Subsequent calls have no effect.

    Note:
        This function is safe to call multiple times. The first call loads .env
        and initializes the runtime; subsequent calls check the initialization
        state and return immediately if already initialized.

        The .env loading lets lib_log_rich read its LOG_* variables from a .env file:
        the highest precedence override for logging configuration.

    Example:
        >>> from lib_layered_config import Config
        >>> config = Config({"lib_log_rich": {"environment": "test"}}, {})
        >>> init_logging(config)  # doctest: +SKIP
    """
    if lib_log_rich.runtime.is_initialised():
        return
    _load_log_variables(dotenv_path)
    try:
        lib_log_rich.runtime.init(_build_runtime_config(config))
    except (ValidationError, ValueError) as exc:
        # The type check of the section and lib_log_rich's own range checks (which also see the
        # LOG_* variables) both refuse here; neither has started the runtime.
        raise InvalidLoggingConfigError(_problems(exc)) from exc
    lib_log_rich.runtime.attach_std_logging()


__all__ = [
    "InvalidLoggingConfigError",
    "LoggingConfigModel",
    "init_logging",
]
