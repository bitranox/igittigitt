"""Real-process shell/piping tests: stdin pipes, NUL separation, and SIGPIPE.

These exercise igittigitt the way scripts use it - as a process at the end of a
pipe - which the in-process CliRunner tests cannot. POSIX-only (SIGPIPE / NUL
find semantics); skipped on Windows.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.os_posix

_SRC_DIR = str(Path(__file__).resolve().parents[1] / "src")


def _env() -> dict[str, str]:
    existing = os.environ.get("PYTHONPATH", "")
    pythonpath = f"{_SRC_DIR}{os.pathsep}{existing}" if existing else _SRC_DIR
    return {**os.environ, "PYTHONPATH": pythonpath}


def _tree(tmp_path: Path) -> Path:
    (tmp_path / ".gitignore").write_text("*.log\nbuild/\n", encoding="utf-8")
    (tmp_path / "a.log").touch()
    (tmp_path / "a.txt").touch()
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "x.o").touch()
    (tmp_path / "keep.py").touch()
    return tmp_path


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX pipes")
def test_find_piped_into_filter(tmp_path: Path) -> None:
    """`find <dir> -type f | igittigitt filter -C <dir>` drops ignored files."""
    _tree(tmp_path)
    find = subprocess.Popen(
        ["find", ".", "-type", "f", "-not", "-name", ".gitignore"],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
    )
    flt = subprocess.run(
        [sys.executable, "-m", "igittigitt", "filter", "-C", str(tmp_path)],
        stdin=find.stdout,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    if find.stdout:
        find.stdout.close()
    find.wait()
    survivors = {line.lstrip("./") for line in flt.stdout.split() if line}
    assert "a.txt" in survivors
    assert "keep.py" in survivors
    assert "a.log" not in survivors
    assert "build/x.o" not in survivors


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX NUL find")
def test_find_print0_piped_into_filter_z(tmp_path: Path) -> None:
    """NUL-separated end to end: `find -print0 | igittigitt filter -z`."""
    _tree(tmp_path)
    find = subprocess.Popen(
        ["find", ".", "-type", "f", "-not", "-name", ".gitignore", "-print0"],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
    )
    flt = subprocess.run(
        [sys.executable, "-m", "igittigitt", "filter", "-C", str(tmp_path), "-z"],
        stdin=find.stdout,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    if find.stdout:
        find.stdout.close()
    find.wait()
    survivors = {tok.lstrip("./") for tok in flt.stdout.split("\0") if tok}
    assert survivors == {"a.txt", "keep.py"}


@pytest.mark.skipif(sys.platform == "win32", reason="SIGPIPE is POSIX-only")
def test_filter_handles_sigpipe_from_head(tmp_path: Path) -> None:
    """`igittigitt filter | head -1` must not crash with a Python traceback."""
    _tree(tmp_path)
    # feed many surviving paths so the writer keeps going after head closes
    many = "\n".join(f"file{i}.txt" for i in range(100_000))
    flt = subprocess.Popen(
        [sys.executable, "-m", "igittigitt", "filter", "-C", str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_env(),
    )
    head = subprocess.Popen(["head", "-n", "1"], stdin=flt.stdout, stdout=subprocess.PIPE, text=True)
    if flt.stdout:
        flt.stdout.close()
    assert flt.stdin is not None
    try:
        flt.stdin.write(many)
        flt.stdin.close()
    except BrokenPipeError:
        pass
    head_out, _ = head.communicate()
    _, flt_err = flt.communicate()
    assert head_out.strip() == "file0.txt"
    assert "Traceback (most recent call last)" not in flt_err
