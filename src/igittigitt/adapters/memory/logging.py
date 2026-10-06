"""In-memory logging adapter for testing.

Starts a quiet, minimal ``lib_log_rich`` runtime, so a command run under the testing
composition has a live runtime to log and bind against.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import lib_log_rich.runtime
from lib_log_rich.domain import LogLevel

from igittigitt import __init__conf__

if TYPE_CHECKING:
    from lib_layered_config import Config


def init_logging_in_memory(config: Config) -> None:
    """Start a quiet lib_log_rich runtime for tests, unless one is already running.

    Every CLI command binds job context onto the process-global runtime
    (``lib_log_rich.runtime.bind(...)``), which raises ``RuntimeError('lib_log_rich.init()
    must be called before using the logging API')`` when no runtime is live. A test double
    that did nothing would therefore make every command fail under ``build_testing()``.

    Journald, the Windows event log, Graylog and the background queue are off: a test
    double has no business writing to a system log, and a queue is a background thread the
    test run would have to reap. The console level is ERROR so ordinary INFO logging cannot
    land in the output a test asserts on. Unlike the production initializer this never loads
    a ``.env`` file, so a test run does not pick up the developer's own environment.

    Args:
        config: Layered configuration object. Unused: the test runtime is fixed, and the
            parameter exists to satisfy the ``InitLogging`` protocol.

    Example:
        >>> from lib_layered_config import Config
        >>> init_logging_in_memory(Config({}, {}))
        >>> lib_log_rich.runtime.is_initialised()
        True
        >>> lib_log_rich.runtime.shutdown()
    """
    if lib_log_rich.runtime.is_initialised():
        return
    lib_log_rich.runtime.init(
        lib_log_rich.runtime.RuntimeConfig(
            service=f"{__init__conf__.name}-test",
            environment="test",
            console_level=LogLevel.ERROR,
            enable_journald=False,
            enable_eventlog=False,
            enable_graylog=False,
            queue_enabled=False,
        )
    )


__all__ = ["init_logging_in_memory"]
