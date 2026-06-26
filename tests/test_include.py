"""Tests for the directory-aware include/whitelist mode."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import igittigitt


def _build_tree(root: Path) -> None:
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "src" / "main.py").write_text("x", encoding="utf-8")
    (root / "src" / "pkg" / "deep.py").write_text("x", encoding="utf-8")
    (root / "src" / "notes.txt").write_text("x", encoding="utf-8")
    (root / "docs" / "guide.md").write_text("x", encoding="utf-8")
    (root / "readme.md").write_text("x", encoding="utf-8")


@pytest.mark.os_agnostic
def test_include_copytree_keeps_only_deep_matches(tmp_path: Path) -> None:
    src = tmp_path / "src_tree"
    src.mkdir()
    _build_tree(src)

    inc = igittigitt.IncludeParser()
    inc.add_rule("*.py", src)

    dst = tmp_path / "dst_tree"
    shutil.copytree(src, dst, ignore=inc.shutil_include)

    copied = sorted(p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file())
    assert copied == ["src/main.py", "src/pkg/deep.py"]
    # parent directories were descended into and exist
    assert (dst / "src" / "pkg").is_dir()


@pytest.mark.os_agnostic
def test_include_directory_pattern_keeps_subtree(tmp_path: Path) -> None:
    src = tmp_path / "src_tree"
    src.mkdir()
    _build_tree(src)

    inc = igittigitt.IncludeParser()
    inc.add_rule("docs/", src)

    dst = tmp_path / "dst_tree"
    shutil.copytree(src, dst, ignore=inc.shutil_include)

    copied = sorted(p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file())
    assert copied == ["docs/guide.md"]


@pytest.mark.os_agnostic
def test_include_negation_reexcludes_within_tree(tmp_path: Path) -> None:
    src = tmp_path / "src_tree"
    src.mkdir()
    _build_tree(src)

    inc = igittigitt.IncludeParser()
    inc.add_rule("src/", src)
    inc.add_rule("!*.txt", src)

    dst = tmp_path / "dst_tree"
    shutil.copytree(src, dst, ignore=inc.shutil_include)

    copied = sorted(p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file())
    assert copied == ["src/main.py", "src/pkg/deep.py"]  # notes.txt re-excluded


@pytest.mark.os_agnostic
def test_include_keep_set_invariants(tmp_path: Path) -> None:
    """Completeness + soundness for files: exactly the matching files are kept.

    (Directories may be descended into conservatively for unanchored patterns,
    so a kept directory is not required to contain a matching descendant.)
    """
    src = tmp_path / "src_tree"
    src.mkdir()
    _build_tree(src)

    inc = igittigitt.IncludeParser()
    inc.add_rule("*.py", src)

    kept_files = {p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file() and inc.match(p)}
    all_py = {p.relative_to(src).as_posix() for p in src.rglob("*.py")}
    assert kept_files == all_py  # every .py kept, nothing else
