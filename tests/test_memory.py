"""Memory-boundedness: igittigitt's own data structures must not grow with the
number of paths processed.

The guarantee is that memory scales with the number of *rules* and the cache
*cap*, never with the number of files. We prove that deterministically by driving
far more distinct directories through the parsers than the cache can hold and
asserting the caches stay within their cap.

(We do not assert on `tracemalloc` peak/retained byte counts: those are dominated
by CPython internals such as `sys.intern` of path components and GC cadence, which
igittigitt does not control and which differ across interpreter builds. The
cache-cap assertions below are the precise, portable proof of *our* boundedness.)
"""

from __future__ import annotations

import pytest

import igittigitt

_BASE = "/synthetic/root"


def _make_ignore_parser() -> igittigitt.IgnoreParser:
    parser = igittigitt.IgnoreParser()
    parser.add_rule("*.log", _BASE)
    parser.add_rule("build/", _BASE)
    parser.add_rule("!keep*.log", _BASE)
    return parser


@pytest.mark.os_agnostic
def test_directory_cache_stays_bounded() -> None:
    """The ignore directory-decision LRU must not grow past its cap, even when far
    more distinct directories are matched than the cap (memory scales with the
    cap, not with the tree)."""
    from igittigitt.igittigitt import _DIR_CACHE_MAX

    parser = _make_ignore_parser()
    for i in range(_DIR_CACHE_MAX * 3):
        parser.match(f"{_BASE}/dir{i}/sub{i}/file{i}.txt")
    assert len(parser._dir_cache) <= _DIR_CACHE_MAX


@pytest.mark.os_agnostic
def test_include_keep_cache_stays_bounded() -> None:
    """The IncludeParser's ancestor-keep LRU must stay within its cap too."""
    from igittigitt.igittigitt import _DIR_CACHE_MAX

    parser = igittigitt.IncludeParser()
    parser.add_rule("*.txt", _BASE)
    for i in range(_DIR_CACHE_MAX * 3):
        parser.match(f"{_BASE}/dir{i}/sub{i}/file{i}.txt")
    assert len(parser._keep_cache) <= _DIR_CACHE_MAX
