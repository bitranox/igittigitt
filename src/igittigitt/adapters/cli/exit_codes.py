"""POSIX-conventional exit codes for CLI error paths.

Provides a single :class:`ExitCode` enum so every ``SystemExit`` raised by a
CLI command carries a meaningful, grep-friendly integer instead of a bare ``1``.

Signal codes (130, 141, 143) are informational constants only — the application
never raises ``SystemExit`` with these values; ``lib_cli_exit_tools`` handles
signal-to-exit-code translation automatically.

Contents:
    * :class:`ExitCode` — IntEnum of all exit codes used by this application.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """POSIX-conventional exit codes for CLI error paths.

    Values follow sysexits.h and errno conventions where applicable:

    * 0-1: generic success / failure
    * 2-13: errno-derived codes (ENOENT, EACCES)
    * 22: EINVAL
    * 78: EX_CONFIG (sysexits.h)
    * 110: ETIMEDOUT
    * 128+N: signal N (informational only)

    Example:
        >>> ExitCode.SUCCESS
        <ExitCode.SUCCESS: 0>
        >>> int(ExitCode.BROKEN_PIPE)
        141
    """

    SUCCESS = 0
    GENERAL_ERROR = 1
    FILE_NOT_FOUND = 2
    PERMISSION_DENIED = 13
    INVALID_ARGUMENT = 22
    CONFIG_ERROR = 78
    TIMEOUT = 110
    SIGNAL_INT = 130
    BROKEN_PIPE = 141
    SIGNAL_TERM = 143


__all__ = ["ExitCode"]
