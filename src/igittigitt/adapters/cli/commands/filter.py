"""The ``filter`` command - a Unix filter that drops ignored (or non-included) paths.

Reads paths from stdin (or arguments) and prints the survivors, streaming so it
stays memory-bounded for very large inputs:

    find . | igittigitt filter            # drop paths ignored by ./.gitignore
    find . | igittigitt filter -r '*.py' --include   # keep only python files
"""

from __future__ import annotations

import pathlib
import sys

import rich_click as click

from ..constants import CLICK_CONTEXT_SETTINGS
from ..exit_codes import ExitCode
from ..typed_click import argument, option
from ._common import (
    build_ignore_parser,
    build_include_parser,
    emit,
    iter_input_paths,
    resolve_path,
    resolve_performance,
    silence_broken_pipe,
)


@click.command("filter", context_settings=CLICK_CONTEXT_SETTINGS)
@option(
    "--base-dir", "-C", "base_dir", default=".", show_default=True, help="Base directory the patterns are relative to."
)
@option("--gitignore", "-f", "rule_files", multiple=True, help="Ignore/include file to parse (repeatable).")
@option("--rule", "-r", "rules", multiple=True, help="Inline rule (repeatable).")
@option(
    "--include",
    "-i",
    "include_mode",
    is_flag=True,
    default=False,
    help="Include/whitelist mode: keep only paths that match.",
)
@option(
    "--scan/--no-scan",
    "scan",
    default=None,
    help="Recursively discover .gitignore files under base-dir (ignore mode). Default: only when no -f/-r given.",
)
@option(
    "--default-patterns/--no-default-patterns",
    "default_patterns",
    default=False,
    help="Also load git's default patterns (ignore mode).",
)
@option("-z", "--zero", "zero", is_flag=True, default=False, help="Input and output are NUL-separated.")
@argument("paths", nargs=-1)
@click.pass_context
def cli_filter(
    ctx: click.Context,
    base_dir: str,
    rule_files: tuple[str, ...],
    rules: tuple[str, ...],
    include_mode: bool,
    scan: bool | None,
    default_patterns: bool,
    zero: bool,
    paths: tuple[str, ...],
) -> None:
    """Print the surviving paths (not ignored, or - with --include - kept)."""
    perf = resolve_performance(ctx)
    if include_mode:
        include_parser = build_include_parser(base_dir, rule_files, rules, dir_cache_max=perf.dir_cache_max)

        def survives(path: pathlib.Path) -> bool:
            return include_parser.match(path)
    else:
        do_scan = scan if scan is not None else not (rule_files or rules)
        ignore_parser = build_ignore_parser(
            base_dir, rule_files, rules, do_scan, default_patterns, dir_cache_max=perf.dir_cache_max
        )

        def survives(path: pathlib.Path) -> bool:
            return not ignore_parser.match(path)

    use_stdin = not paths or tuple(paths) == ("-",)
    out = sys.stdout
    try:
        for token in iter_input_paths(
            paths,
            use_stdin=use_stdin,
            zero=zero,
            chunk_bytes=perf.stdin_chunk_bytes,
            max_token_bytes=perf.max_token_bytes,
        ):
            if survives(resolve_path(token, base_dir)):
                emit(token, zero=zero, out=out)
        out.flush()
    except BrokenPipeError:
        silence_broken_pipe()
        raise SystemExit(ExitCode.BROKEN_PIPE) from None


__all__ = ["cli_filter"]
