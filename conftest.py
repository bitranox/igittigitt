"""Keep the machine's configuration layers out of every test AND every doctest.

These fixtures live in the rootdir conftest rather than ``tests/conftest.py`` because
``--doctest-modules`` also collects the doctests under ``src/``, and a conftest's fixtures reach only
the items below its own directory. ``testpaths`` in pyproject keeps this file itself out of doctest
collection; without it pytest imports it a second time as module ``conftest`` and collides with
``tests/conftest.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from layer_roots import SYSTEM_LAYER_ROOT_VARIABLES, USER_LAYER_ROOT_VARIABLES

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def system_layers_in_tmp_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the app and host configuration layers at an empty directory under ``tmp_path``.

    A machine with the CLI deployed system-wide would otherwise decide results: a value in its
    ``/etc/xdg/<slug>/config.d/`` fails tests there while a clean CI runner stays green. A
    subprocess inherits the redirect through ``os.environ``; one that builds its own environment
    must carry these variables over (see ``layer_roots.SYSTEM_LAYER_ROOT_VARIABLES``).

    Returns:
        The redirected root, so a test can place a file in the app or host layer.
    """
    root = tmp_path / "system-layers"
    for name in SYSTEM_LAYER_ROOT_VARIABLES:
        monkeypatch.setenv(name, str(root))
    return root


@pytest.fixture(autouse=True)
def user_layer_in_tmp_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point every OS's user configuration layer at an empty directory under ``tmp_path``.

    A developer with a user-layer deploy (``~/.config/<slug>/config.d/99-*.toml``) would otherwise
    decide results on their machine while a clean CI runner stays green, and a test running
    ``config-deploy --target user`` would write into their real configuration. A subprocess inherits
    the redirect through ``os.environ``. The root is not created, so a test can assert that nothing
    was written under ``tmp_path``.

    Returns:
        The redirected root, so a test can place a file in the user layer or find what a deploy wrote.
    """
    root = tmp_path / "user-layer"
    for name in USER_LAYER_ROOT_VARIABLES:
        monkeypatch.setenv(name, str(root))
    return root
