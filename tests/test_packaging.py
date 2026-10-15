"""The source distribution carries the package, its tests and its docs, and nothing else.

A working tree holds files that must never be published: session records, backlogs, scratch
review notes and helper scripts. Some are tracked, some are hidden only through
``.git/info/exclude`` or a nested ``.gitignore``, which hatchling does not read. The sdist is
therefore built from an allowlist, and this test builds one from a copy of the tree that also
holds such decoys. The wheel must still carry the package data the runtime loads.
"""

from __future__ import annotations

import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest
from hatchling.builders.sdist import SdistBuilder
from hatchling.builders.wheel import WheelBuilder

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "igittigitt"

# hatchling force-includes the root .gitignore into every sdist (so a build from the unpacked
# sdist applies the same exclusions); no include/exclude setting removes it.
ALLOWED_TOP_LEVEL = frozenset(
    {
        "PKG-INFO",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        ".gitignore",
        "src",
        "tests",
        "docs",
    }
)
REQUIRED_TOP_LEVEL = frozenset({"PKG-INFO", "pyproject.toml", "src", "tests"})

# Files and directories that exist in working trees and must never ship. Tracked ones are
# named in the repository; the others are hidden locally through .git/info/exclude.
DECOY_FILES = ("handover.md", "OPEN-WORK.md", "EXECUTION-USER-REVIEW.md", "reset_git_history.sh", ".private/notes.txt")

REQUIRED_WHEEL_DATA = (
    "igittigitt/py.typed",
    "igittigitt/adapters/config/defaultconfig.toml",
)


def _copy_tree_with_decoys(destination: Path) -> Path:
    """Copy the buildable tree and plant the files a working tree carries but must not ship."""
    root = destination / "tree"
    root.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE", "CHANGELOG.md", ".gitignore"):
        shutil.copy2(PROJECT_ROOT / name, root / name)
    for name in ("src", "docs", "tests"):
        shutil.copytree(PROJECT_ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for decoy in DECOY_FILES:
        path = root / decoy
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("decoy\n", encoding="utf-8")
    return root


def _build_sdist(root: Path, directory: Path) -> Path:
    built = list(SdistBuilder(str(root)).build(directory=str(directory), versions=["standard"]))
    assert len(built) == 1, f"expected one sdist, got {built}"
    return Path(built[0])


def _strip_root(names: list[str]) -> list[str]:
    """Drop the ``<name>-<version>/`` prefix every member carries."""
    return [name.split("/", 1)[1] for name in names if "/" in name]


@pytest.fixture(scope="module")
def built_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _copy_tree_with_decoys(tmp_path_factory.mktemp("packaging"))


@pytest.fixture(scope="module")
def sdist_members(built_tree: Path, tmp_path_factory: pytest.TempPathFactory) -> list[str]:
    sdist = _build_sdist(built_tree, tmp_path_factory.mktemp("sdist"))
    with tarfile.open(sdist, "r:gz") as archive:
        members = _strip_root(archive.getnames())
    assert members, "the sdist is empty, so nothing below would be judged"
    return members


@pytest.fixture(scope="module")
def wheel_members(built_tree: Path, tmp_path_factory: pytest.TempPathFactory) -> list[str]:
    built = list(
        WheelBuilder(str(built_tree)).build(directory=str(tmp_path_factory.mktemp("wheel")), versions=["standard"])
    )
    assert len(built) == 1, f"expected one wheel, got {built}"
    with zipfile.ZipFile(built[0]) as archive:
        members = archive.namelist()
    assert members, "the wheel is empty, so nothing below would be judged"
    return members


@pytest.mark.os_agnostic
def test_the_sdist_holds_only_allowlisted_top_level_entries(sdist_members: list[str]) -> None:
    top_level = {member.split("/", 1)[0] for member in sdist_members}

    unexpected = sorted(top_level - ALLOWED_TOP_LEVEL)
    missing = sorted(REQUIRED_TOP_LEVEL - top_level)

    assert not unexpected, f"the sdist ships files outside the allowlist: {unexpected}"
    assert not missing, f"the sdist lacks required entries: {missing}"


@pytest.mark.os_agnostic
def test_the_sdist_ships_only_the_package_under_src(sdist_members: list[str]) -> None:
    under_src = {
        member.split("/")[1] for member in sdist_members if member.startswith("src/") and member.count("/") >= 1
    }

    assert under_src == {PACKAGE}


@pytest.mark.os_agnostic
def test_the_sdist_carries_no_compiled_bytecode(sdist_members: list[str]) -> None:
    compiled = [member for member in sdist_members if "__pycache__" in member.split("/") or member.endswith(".pyc")]

    assert not compiled, f"the sdist ships bytecode: {compiled[:5]}"


@pytest.mark.os_agnostic
def test_the_wheel_carries_the_package_data_the_runtime_loads(wheel_members: list[str]) -> None:
    missing = [name for name in REQUIRED_WHEEL_DATA if name not in wheel_members]

    assert not missing, f"the wheel lacks package data: {missing}"
