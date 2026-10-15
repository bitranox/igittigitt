"""The ``os_*`` markers skip a test off its platform; registering them alone would skip nothing.

Each test asserts the platform its own marker names, so it fails wherever conftest lets it run by
mistake, and passes where the marker lets it run.
"""

from __future__ import annotations

import sys

import pytest


@pytest.mark.os_windows
def test_an_os_windows_test_runs_only_on_windows() -> None:
    assert sys.platform == "win32"


@pytest.mark.os_macos
def test_an_os_macos_test_runs_only_on_macos() -> None:
    assert sys.platform == "darwin"


@pytest.mark.os_linux
def test_an_os_linux_test_runs_only_on_linux() -> None:
    assert sys.platform.startswith("linux")


@pytest.mark.os_posix
def test_an_os_posix_test_never_runs_on_windows() -> None:
    assert sys.platform != "win32"
