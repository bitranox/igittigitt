"""Differential tests: igittigitt must agree with real ``git`` on every path.

For each scenario we build a throwaway git repository, write the ``.gitignore``
file(s), create the real files/directories, then ask ``git check-ignore`` (the
oracle) about every path and compare with :class:`igittigitt.IgnoreParser`.

The git invocation is made deterministic by neutralising the user/global/system
git configuration (no ``core.excludesFile``, no ``~/.gitconfig``), so the result
depends only on the in-repo ``.gitignore`` files.

The whole module is skipped when ``git`` is not on PATH.
"""

from __future__ import annotations

import random
import shutil
import subprocess
from pathlib import Path

import pytest

import igittigitt

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

_GIT = shutil.which("git") or "git"


def _git_env() -> dict[str, str]:
    import os

    return {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": "/nonexistent-igittigitt-home",
    }


def _init_repo(root: Path) -> None:
    subprocess.run([_GIT, "init", "-q", str(root)], check=True, env=_git_env())
    subprocess.run(
        [_GIT, "-C", str(root), "config", "core.excludesFile", "/dev/null"],
        check=True,
        env=_git_env(),
    )


def _git_ignored(root: Path, rel_paths: list[str]) -> set[str]:
    """Return the subset of *rel_paths* that git reports as ignored (the oracle)."""
    payload = "\0".join(rel_paths)
    result = subprocess.run(
        [_GIT, "-C", str(root), "check-ignore", "--stdin", "-z", "--no-index"],
        input=payload,
        capture_output=True,
        text=True,
        env=_git_env(),
        check=False,
    )
    # exit 0: some matched, 1: none matched, >1: error
    assert result.returncode in (0, 1), result.stderr
    return {token for token in result.stdout.split("\0") if token}


def _materialise(root: Path, files: list[str], gitignores: dict[str, str]) -> None:
    for rel, content in gitignores.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    for rel in files:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.touch()


def _all_relpaths(root: Path) -> list[str]:
    """Every file and directory under root (relative, posix), excluding .git."""
    out: list[str] = []
    for path in sorted(root.rglob("*")):
        if ".git" in path.relative_to(root).parts:
            continue
        out.append(path.relative_to(root).as_posix())
    return out


def _assert_matches_git(tmp_path: Path, gitignores: dict[str, str], files: list[str]) -> None:
    _init_repo(tmp_path)
    _materialise(tmp_path, files, gitignores)

    rel_paths = _all_relpaths(tmp_path)
    oracle = _git_ignored(tmp_path, rel_paths)

    parser = igittigitt.IgnoreParser()
    parser.parse_rule_files(base_dir=tmp_path, add_default_patterns=False)

    mismatches: list[str] = []
    for rel in rel_paths:
        mine = parser.match(tmp_path / rel)
        theirs = rel in oracle
        if mine != theirs:
            mismatches.append(f"{rel}: igittigitt={mine} git={theirs}")
    assert not mismatches, "disagreement with git:\n" + "\n".join(mismatches)


# Each scenario: (gitignore-files, list-of-paths-to-create)
SCENARIOS: dict[str, tuple[dict[str, str], list[str]]] = {
    "basic_globs": (
        {".gitignore": "*.log\n*.tmp\nbuild/\n"},
        ["a.log", "a.txt", "x.tmp", "build/out.o", "build/sub/deep.o", "src/main.py", "src/main.log"],
    ),
    "negation_simple": (
        {".gitignore": "*.log\n!keep.log\n"},
        ["a.log", "keep.log", "sub/keep.log", "sub/a.log"],
    ),
    "negation_under_excluded_dir": (
        {".gitignore": "build/\n!build/keep.txt\n"},
        ["build/keep.txt", "build/other.txt", "build/sub/x.txt"],
    ),
    "reinclude_dir_chain": (
        {".gitignore": "/*\n!/foo\n/foo/*\n!/foo/bar\n"},
        ["foo/bar/file.txt", "foo/other/file.txt", "top.txt", "foo/keep"],
    ),
    "anchored_vs_floating": (
        {".gitignore": "/root_only.txt\nfloating.txt\ndir/anchored.txt\n"},
        [
            "root_only.txt",
            "sub/root_only.txt",
            "floating.txt",
            "sub/floating.txt",
            "dir/anchored.txt",
            "other/dir/anchored.txt",
        ],
    ),
    "double_star": (
        {".gitignore": "**/logs\na/**/b\nc/**\n"},
        ["logs/x", "deep/logs/y", "a/b", "a/x/y/b", "c/anything", "c/deep/file", "keep/c"],
    ),
    "char_class": (
        {".gitignore": "*.py[cod]\nfile[0-9].txt\n"},
        ["m.pyc", "m.pyo", "m.pyd", "m.py", "file1.txt", "fileA.txt"],
    ),
    "trailing_slash_dir_only": (
        {".gitignore": "cache/\n"},
        ["cache/x", "cache/sub/y", "sub/cache/z"],
    ),
    "nested_gitignore_precedence": (
        {
            ".gitignore": "*.txt\n",
            "sub/.gitignore": "!important.txt\n",
        },
        ["a.txt", "sub/a.txt", "sub/important.txt", "sub/deep/important.txt"],
    ),
    "comments_and_blanks": (
        {".gitignore": "# a comment\n\n*.bak\n  \n!special.bak\n"},
        ["x.bak", "special.bak", "dir/special.bak"],
    ),
}


@pytest.mark.os_posix
@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_matches_git(name: str, tmp_path: Path) -> None:
    gitignores, files = SCENARIOS[name]
    _assert_matches_git(tmp_path, gitignores, files)


# --- randomized fuzz against git (fixed seed -> deterministic) ----------------

_SEGMENTS = ["a", "b", "c", "src", "build", "logs", "node_modules", "x", "y"]
_LEAVES = ["main.py", "a.log", "x.tmp", "keep.txt", "data.bin", "m.pyc", "file1.txt", "readme"]


def _random_pattern(rng: random.Random) -> str:
    body_choices = [
        "*.log",
        "*.tmp",
        "*.py[cod]",
        "build/",
        "logs/",
        "**/logs",
        "node_modules/",
        "/src",
        "src/*.py",
        "a/**/b",
        "c/**",
        "file?.txt",
        rng.choice(_SEGMENTS),
        f"{rng.choice(_SEGMENTS)}/{rng.choice(_SEGMENTS)}",
        f"{rng.choice(_SEGMENTS)}/",
    ]
    pattern = rng.choice(body_choices)
    if rng.random() < 0.25:
        pattern = "!" + pattern
    return pattern


def _random_relpath(rng: random.Random) -> str:
    depth = rng.randint(0, 3)
    parts = [rng.choice(_SEGMENTS) for _ in range(depth)]
    parts.append(rng.choice(_LEAVES))
    return "/".join(parts)


@pytest.mark.os_posix
@pytest.mark.parametrize("seed", range(40))
def test_matches_git_fuzz(seed: int, tmp_path: Path) -> None:
    rng = random.Random(seed)
    n_rules = rng.randint(1, 8)
    gitignore = "\n".join(_random_pattern(rng) for _ in range(n_rules)) + "\n"
    files = sorted({_random_relpath(rng) for _ in range(rng.randint(3, 12))})
    _assert_matches_git(tmp_path, {".gitignore": gitignore}, files)
