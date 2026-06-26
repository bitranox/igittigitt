"""Memory-boundedness: matching a huge stream of paths must not grow memory.

The parsers hold only the compiled rules; per-path matching must not allocate
anything that grows with the number of paths processed. We stream a synthetic
tree of paths (a generator, never materialised) through ``match`` and assert the
peak additional allocation stays flat between a small and a large run.
"""

from __future__ import annotations

import tracemalloc
from collections.abc import Iterator

import pytest

import igittigitt

_BASE = "/synthetic/root"


def _synthetic_paths(count: int) -> Iterator[str]:
    """Yield *count* distinct deep paths without building a list."""
    for i in range(count):
        a, b, c = i % 50, (i // 50) % 50, i % 7
        yield f"{_BASE}/dir{a}/sub{b}/build/file{i}.log" if c == 0 else f"{_BASE}/dir{a}/sub{b}/file{i}.txt"


def _peak_for(parser: object, count: int) -> int:
    matcher = parser.match  # type: ignore[attr-defined]
    tracemalloc.start()
    tracemalloc.reset_peak()
    for path in _synthetic_paths(count):
        matcher(path)
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return peak


def _make_ignore_parser() -> igittigitt.IgnoreParser:
    parser = igittigitt.IgnoreParser()
    parser.add_rule("*.log", _BASE)
    parser.add_rule("build/", _BASE)
    parser.add_rule("!keep*.log", _BASE)
    return parser


@pytest.mark.os_agnostic
def test_ignore_match_memory_is_bounded() -> None:
    parser = _make_ignore_parser()
    # warm up caches/interning
    _peak_for(parser, 1_000)

    small = _peak_for(parser, 3_000)
    large = _peak_for(parser, 30_000)

    # 10x the paths must not meaningfully grow peak memory (allow generous slack
    # for interpreter noise); a per-path leak would make `large` ~10x `small`.
    assert large < small + 200_000, f"memory grew with path count: small={small} large={large}"


@pytest.mark.os_agnostic
def test_directory_cache_stays_bounded() -> None:
    """The directory-decision LRU must not grow past its cap, even across many
    distinct directories (memory scales with the cap, not with the tree)."""
    from igittigitt.igittigitt import _DIR_CACHE_MAX

    parser = _make_ignore_parser()
    # touch far more distinct directories than the cache cap
    for i in range(_DIR_CACHE_MAX * 3):
        parser.match(f"{_BASE}/dir{i}/sub{i}/file{i}.txt")
    assert len(parser._dir_cache) <= _DIR_CACHE_MAX


@pytest.mark.os_agnostic
def test_include_match_memory_is_bounded() -> None:
    parser = igittigitt.IncludeParser()
    parser.add_rule("*.txt", _BASE)

    _peak_for(parser, 1_000)
    small = _peak_for(parser, 3_000)
    large = _peak_for(parser, 30_000)

    assert large < small + 200_000, f"memory grew with path count: small={small} large={large}"


@pytest.mark.os_agnostic
def test_include_keep_cache_stays_bounded() -> None:
    """The IncludeParser's ancestor-keep LRU must stay within its cap too."""
    from igittigitt.igittigitt import _DIR_CACHE_MAX

    parser = igittigitt.IncludeParser()
    parser.add_rule("*.txt", _BASE)
    for i in range(_DIR_CACHE_MAX * 3):
        parser.match(f"{_BASE}/dir{i}/sub{i}/file{i}.txt")
    assert len(parser._keep_cache) <= _DIR_CACHE_MAX
