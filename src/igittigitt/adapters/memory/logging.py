"""In-memory logging adapter for testing.

Provides a no-op logging initializer that satisfies the InitLogging protocol.
"""

from __future__ import annotations

from lib_layered_config import Config


def init_logging_in_memory(config: Config) -> None:
    """No-op -- satisfies the InitLogging protocol without side effects."""


__all__ = ["init_logging_in_memory"]
