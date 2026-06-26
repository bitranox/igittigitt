"""igittigitt - a spec-compliant ``.gitignore`` parser for Python.

Public API:
    * :class:`IgnoreParser` - parse ``.gitignore`` rules and test paths, or use
      ``shutil_ignore`` as the ``ignore=`` callback of ``shutil.copytree``.
    * :class:`IncludeParser` - the inverse (whitelist / include) mode, directory
      aware, with ``shutil_include`` for ``shutil.copytree``.
    * :data:`conf_igittigitt` - runtime configuration.
    * :func:`print_info` - render package metadata (used by the CLI ``info``).
"""

from __future__ import annotations

from . import __init__conf__
from .__init__conf__ import print_info
from .conf_igittigitt import conf_igittigitt
from .igittigitt import IgnoreParser, IncludeParser

__all__ = [
    "IgnoreParser",
    "IncludeParser",
    "conf_igittigitt",
    "print_info",
    "__init__conf__",
]
