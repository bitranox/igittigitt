"""POSIX-conventional exit codes for CLI error paths.

Provides a single :class:`ExitCode` enum so every ``SystemExit`` raised by a
CLI command carries a meaningful, grep-friendly integer instead of a bare ``1``.

``SIGNAL_INT`` (130) and ``SIGNAL_TERM`` (143) are informational constants only:
``lib_cli_exit_tools`` translates those signals to exit codes automatically, so
the application never raises them itself. ``BROKEN_PIPE`` (141) is the exception
and IS raised directly, by ``check`` and ``filter``, when their output pipe closes
early (``head``, a closed pager); a signal handler cannot cover that, because
Python surfaces it as a ``BrokenPipeError`` rather than a ``SIGPIPE``.

Contents:
    * :class:`ExitCode` - IntEnum of all exit codes used by this application.
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
    * 128+N: signal N (informational, except BROKEN_PIPE - see the module docstring)

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
