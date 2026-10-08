"""Every third-party module the package imports at run time is a declared dependency.

A module that is only installed because another dependency pulls it in works until that
dependency drops it or caps its version, and then the package breaks for a reason its own
metadata never mentioned. Imports under ``if TYPE_CHECKING:`` are not counted: they never
run in an installed package.
"""

from __future__ import annotations

import ast
import re
import sys
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest
import rtoml

_ROOT = Path(__file__).parent.parent
_PACKAGE = "igittigitt"
_SOURCE = _ROOT / "src" / _PACKAGE
#: The package's own top-level modules. ``igittigitt.py`` falls back to a bare
#: ``from conf_igittigitt import ...`` when it runs outside the package; that names a sibling
#: file of this package, not a third-party distribution.
_OWN_MODULES = frozenset(path.stem for path in _SOURCE.glob("*.py"))


def _normalise(name: str) -> str:
    """PEP 503 name normalisation, so ``rich_click`` and ``rich-click`` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_distributions() -> set[str]:
    requirements: list[str] = rtoml.load(_ROOT / "pyproject.toml")["project"]["dependencies"]
    names = (re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement) for requirement in requirements)
    return {_normalise(match.group(0)) for match in names if match}


def _is_type_checking_block(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _runtime_imports(tree: ast.AST) -> set[str]:
    """Top-level module names imported outside ``if TYPE_CHECKING:`` blocks."""
    found: set[str] = set()
    pending: list[ast.AST] = [tree]
    while pending:
        node = pending.pop()
        if _is_type_checking_block(node):
            continue
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
        pending.extend(ast.iter_child_nodes(node))
    return found


def _third_party_runtime_imports() -> dict[str, list[str]]:
    """Each third-party top-level module the package imports at run time, with its importers."""
    importers: dict[str, list[str]] = {}
    for path in sorted(_SOURCE.rglob("*.py")):
        for module in _runtime_imports(ast.parse(path.read_text(encoding="utf-8"))):
            if module in sys.stdlib_module_names or module == _PACKAGE or module in _OWN_MODULES:
                continue
            importers.setdefault(module, []).append(str(path.relative_to(_ROOT)))
    return importers


@pytest.mark.os_agnostic
def test_the_scan_sees_the_package_s_own_third_party_imports() -> None:
    """Control: the scan must find imports it is known to contain, or an empty result proves nothing."""
    assert {"pydantic", "lib_layered_config", "rich_click"} <= set(_third_party_runtime_imports())


@pytest.mark.os_agnostic
def test_every_runtime_import_is_a_declared_dependency() -> None:
    declared = _declared_distributions()
    providers = packages_distributions()

    undeclared = {
        module: importers
        for module, importers in _third_party_runtime_imports().items()
        if not {_normalise(dist) for dist in providers.get(module, [module])} & declared
    }

    assert undeclared == {}, f"imported at run time but not in [project].dependencies: {undeclared}"
