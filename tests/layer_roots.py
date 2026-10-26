"""The environment variables that place lib_layered_config's configuration layers.

The rootdir ``conftest.py`` points every one of them under ``tmp_path`` for each test and doctest.
A test that builds its own subprocess environment from scratch reads them here to carry the
redirect over. Imported by bare name: ``pythonpath`` in pyproject puts ``tests/`` on ``sys.path``
before any conftest loads, so the rootdir conftest and the tests share this one module.
"""

from __future__ import annotations

__all__ = ["SYSTEM_LAYER_ROOT_VARIABLES", "USER_LAYER_ROOT_VARIABLES"]

#: The variables lib_layered_config reads the app and host layers' root from, one per platform.
#: All three are set on every OS: Windows looks up ``ProgramData`` in mixed case after
#: ``LIB_LAYERED_CONFIG_PROGRAMDATA``, while ``os.environ`` upper-cases its keys there, so redirecting
#: ``PROGRAMDATA`` alone still reads the real ``C:\ProgramData``.
SYSTEM_LAYER_ROOT_VARIABLES: tuple[str, ...] = (
    "LIB_LAYERED_CONFIG_ETC",
    "LIB_LAYERED_CONFIG_MAC_APP_ROOT",
    "LIB_LAYERED_CONFIG_PROGRAMDATA",
)

#: The variables lib_layered_config reads the user layer's root from, one per platform: Linux's
#: ``XDG_CONFIG_HOME`` (which also places the user-layer ``.env``), and on macOS and Windows its own
#: overrides, which it consults before ``HOME`` / ``APPDATA`` / ``LOCALAPPDATA``. Redirecting ``HOME``
#: instead would also move git's and uv's configuration for every subprocess the suite starts.
USER_LAYER_ROOT_VARIABLES: tuple[str, ...] = (
    "XDG_CONFIG_HOME",
    "LIB_LAYERED_CONFIG_MAC_HOME_ROOT",
    "LIB_LAYERED_CONFIG_APPDATA",
    "LIB_LAYERED_CONFIG_LOCALAPPDATA",
)
