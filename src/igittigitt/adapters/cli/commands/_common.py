"""Shared helpers for the scripting commands (``check`` / ``filter``).

These helpers keep memory bounded: input paths are streamed token by token
(newline or NUL separated) and results are written immediately, so the commands
work on inputs of millions of paths without buffering them.
"""

from __future__ import annotations

import os
import pathlib
import sys
from typing import TYPE_CHECKING, TextIO

import rich_click as click

from igittigitt.adapters.config.performance import (
    PerformanceSettings,
    apply_process_wide,
    load_performance_settings,
)
from igittigitt.igittigitt import IgnoreParser, IncludeParser

from ..context import get_cli_context

if TYPE_CHECKING:
    from collections.abc import Iterator

_CHUNK = 65536
#: Upper bound for a single input token (path) while no separator has been seen.
#: Guards the bounded-memory guarantee against a separator-less giant stream.
_MAX_TOKEN_BYTES = 1 << 20  # 1 MiB


def build_ignore_parser(
    base_dir: str,
    *,
    ignore_files: tuple[str, ...],
    rules: tuple[str, ...],
    scan: bool,
    add_default_patterns: bool,
    dir_cache_max: int | None = None,
) -> IgnoreParser:
    """Assemble an :class:`IgnoreParser` from CLI inputs (order: scan, files, rules)."""
    parser = IgnoreParser() if dir_cache_max is None else IgnoreParser(dir_cache_max=dir_cache_max)
    if scan:
        parser.parse_rule_files(base_dir, add_default_patterns=add_default_patterns)
    elif add_default_patterns:
        parser.load_default_patterns(base_dir)
    for ignore_file in ignore_files:
        parser.parse_rule_file(ignore_file, base_dir=base_dir)
    for rule in rules:
        parser.add_rule(rule, base_dir)
    return parser


def build_include_parser(
    base_dir: str,
    include_files: tuple[str, ...],
    rules: tuple[str, ...],
    dir_cache_max: int | None = None,
) -> IncludeParser:
    """Assemble an :class:`IncludeParser` from CLI inputs (files then rules)."""
    parser = IncludeParser() if dir_cache_max is None else IncludeParser(dir_cache_max=dir_cache_max)
    for include_file in include_files:
        parser.parse_rule_file(include_file, base_dir=base_dir)
    for rule in rules:
        parser.add_rule(rule, base_dir)
    return parser


def iter_input_paths(
    paths: tuple[str, ...],
    *,
    use_stdin: bool,
    zero: bool,
    stream: TextIO | None = None,
    chunk_bytes: int = _CHUNK,
    max_token_bytes: int = _MAX_TOKEN_BYTES,
) -> Iterator[str]:
    """Yield input path tokens, streamed from args or stdin.

    Args:
        paths: Positional path arguments (used when not reading stdin).
        use_stdin: Read tokens from ``stream`` (default stdin) instead of args.
        zero: Tokens are NUL-separated rather than newline-separated.
        stream: Optional input stream override (defaults to ``sys.stdin``).
        chunk_bytes: stdin read granularity (config knob ``stdin_chunk_bytes``).
        max_token_bytes: per-token safety bound (config knob ``max_token_bytes``).
    """
    if use_stdin:
        sep = "\0" if zero else "\n"
        source = stream if stream is not None else sys.stdin
        yield from _iter_stream_tokens(source, sep, chunk_bytes, max_token_bytes)
    else:
        yield from paths


def _iter_stream_tokens(stream: TextIO, sep: str, chunk_bytes: int, max_token_bytes: int) -> Iterator[str]:
    """Stream tokens from *stream* split on *sep* without buffering all input.

    Raises:
        click.UsageError: if a single token grows past *max_token_bytes* without
            a separator - this keeps memory bounded even for a pathological
            separator-less stream.
    """
    buffer = ""
    while True:
        chunk = stream.read(chunk_bytes)
        if not chunk:
            break
        buffer += chunk
        parts = buffer.split(sep)
        buffer = parts.pop()
        for part in parts:
            token = part.rstrip("\r") if sep == "\n" else part
            if token:
                yield token
        if len(buffer) > max_token_bytes:
            raise click.UsageError(f"input path token exceeds {max_token_bytes} bytes; missing separator?")
    tail = buffer.rstrip("\r") if sep == "\n" else buffer
    if tail:
        yield tail


def resolve_path(token: str, base_dir: str) -> pathlib.Path:
    """Resolve an input token against *base_dir* (absolute tokens kept as-is)."""
    candidate = pathlib.Path(token)
    if candidate.is_absolute():
        return candidate
    return pathlib.Path(base_dir) / candidate


def emit(value: str, *, zero: bool, out: TextIO) -> None:
    """Write *value* followed by the configured separator."""
    out.write(value + ("\0" if zero else "\n"))


def resolve_performance(ctx: click.Context) -> PerformanceSettings:
    """Load the ``[performance]`` knobs from the CLI context and apply the
    process-wide ones (the compiled-pattern cache size)."""
    settings = load_performance_settings(get_cli_context(ctx).config)
    apply_process_wide(settings)
    return settings


def silence_broken_pipe() -> None:
    """Redirect stdout to the null device so the interpreter shutdown flush does
    not re-raise ``BrokenPipeError`` after a downstream reader (e.g. ``head``)
    closed the pipe."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())


__all__ = [
    "build_ignore_parser",
    "build_include_parser",
    "emit",
    "iter_input_paths",
    "resolve_path",
    "resolve_performance",
    "silence_broken_pipe",
]
