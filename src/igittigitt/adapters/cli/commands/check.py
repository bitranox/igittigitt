"""The ``check`` command - report which paths are ignored (like ``git check-ignore``)."""

from __future__ import annotations

import sys

import rich_click as click

from ..constants import CLICK_CONTEXT_SETTINGS
from ..exit_codes import ExitCode
from ..typed_click import argument, option
from ._common import (
    build_ignore_parser,
    emit,
    iter_input_paths,
    resolve_path,
    resolve_performance,
    silence_broken_pipe,
)


@click.command("check", context_settings=CLICK_CONTEXT_SETTINGS)
@option(
    "--base-dir", "-C", "base_dir", default=".", show_default=True, help="Base directory the patterns are relative to."
)
@option("--gitignore", "-f", "ignore_files", multiple=True, help="Ignore file to parse (repeatable).")
@option("--rule", "-r", "rules", multiple=True, help="Inline ignore rule (repeatable).")
@option(
    "--scan/--no-scan",
    "scan",
    default=None,
    help="Recursively discover .gitignore files under base-dir. Default: only when no -f/-r given.",
)
@option(
    "--default-patterns/--no-default-patterns",
    "default_patterns",
    default=False,
    help="Also load git's default patterns from the user home.",
)
@option(
    "--stdin",
    "stdin_flag",
    is_flag=True,
    default=False,
    help="Read paths from stdin (one per line, or NUL-separated with -z).",
)
@option("-z", "--zero", "zero", is_flag=True, default=False, help="Input and output are NUL-separated.")
@option("-v", "--verbose", "verbose", is_flag=True, default=False, help="Also print the matching source:line:pattern.")
@argument("paths", nargs=-1)
@click.pass_context
def cli_check(
    ctx: click.Context,
    base_dir: str,
    ignore_files: tuple[str, ...],
    rules: tuple[str, ...],
    scan: bool | None,
    default_patterns: bool,
    stdin_flag: bool,
    zero: bool,
    verbose: bool,
    paths: tuple[str, ...],
) -> None:
    """Print the paths that are ignored. Exit 0 if any matched, 1 if none."""
    perf = resolve_performance(ctx)
    do_scan = scan if scan is not None else not (ignore_files or rules)
    parser = build_ignore_parser(
        base_dir, ignore_files, rules, do_scan, default_patterns, dir_cache_max=perf.dir_cache_max
    )

    use_stdin = stdin_flag or not paths or tuple(paths) == ("-",)
    out = sys.stdout
    any_match = False
    try:
        for token in iter_input_paths(
            paths,
            use_stdin=use_stdin,
            zero=zero,
            chunk_bytes=perf.stdin_chunk_bytes,
            max_token_bytes=perf.max_token_bytes,
        ):
            ignored, rule = parser.match_with_rule(resolve_path(token, base_dir))
            if not ignored:
                continue
            any_match = True
            if verbose and rule is not None:
                source = str(rule.source_file) if rule.source_file is not None else ""
                line = rule.source_line_number if rule.source_line_number is not None else ""
                emit(f"{source}:{line}:{rule.pattern_original}\t{token}", zero=zero, out=out)
            else:
                emit(token, zero=zero, out=out)
        out.flush()
    except BrokenPipeError:
        silence_broken_pipe()
        raise SystemExit(ExitCode.BROKEN_PIPE) from None

    raise SystemExit(ExitCode.SUCCESS if any_match else ExitCode.GENERAL_ERROR)


__all__ = ["cli_check"]
