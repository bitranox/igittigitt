"""The ``check`` command - report which paths are ignored (like ``git check-ignore``)."""

from __future__ import annotations

import os
import pathlib
import sys
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from typing import TextIO

    from ....igittigitt import IgnoreRule


def _source_label(rule: IgnoreRule, base_root: pathlib.Path) -> str:
    """Name the rule's file as git does: relative to the base directory (git: the repository
    root) when the file lies below it, as given otherwise; empty for an inline ``-r`` rule."""
    if rule.source_file is None:
        return ""
    source = pathlib.Path(rule.source_file)
    try:
        return source.relative_to(base_root).as_posix()
    except ValueError:
        return str(source)


def _emit_verbose(rule: IgnoreRule, token: str, *, base_root: pathlib.Path, zero: bool, out: TextIO) -> None:
    """Write one ``git check-ignore -v`` record: ``source:line:pattern<TAB>path``, or with ``-z``
    every one of the four fields NUL-terminated, as git writes them."""
    line = "" if rule.source_line_number is None else str(rule.source_line_number)
    fields = (_source_label(rule, base_root), line, rule.pattern_original, token)
    if zero:
        out.write("".join(field + "\0" for field in fields))
    else:
        out.write(f"{fields[0]}:{fields[1]}:{fields[2]}\t{fields[3]}\n")


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
@option(
    "-v",
    "--verbose",
    "verbose",
    is_flag=True,
    default=False,
    help="Also print the deciding source:line:pattern, negations included (like git check-ignore -v).",
)
@argument("paths", nargs=-1)
@click.pass_context
def cli_check(
    ctx: click.Context,
    *,
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
    """Print the paths that are ignored. Exit 0 if any matched, 1 if none.

    With -v, a path whose deciding rule is a negation is printed too and counts as matched, as
    git check-ignore -v does; the rule file is named relative to --base-dir when it lies below it.
    """
    perf = resolve_performance(ctx)
    do_scan = scan if scan is not None else not (ignore_files or rules)
    parser = build_ignore_parser(
        base_dir,
        ignore_files=ignore_files,
        rules=rules,
        scan=do_scan,
        add_default_patterns=default_patterns,
        dir_cache_max=perf.dir_cache_max,
    )

    use_stdin = stdin_flag or not paths or tuple(paths) == ("-",)
    # Expanded as the engine expands it (absolute and normalised, symlinks NOT resolved), so the
    # rule files it found compare equal under relative_to; resolve() would follow a symlink.
    base_root = pathlib.Path(os.path.normpath(pathlib.Path(base_dir).expanduser().absolute()))
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
            # git -v reports the deciding rule even when it is a negation, and counts that path
            # for the exit status; without -v only an ignored path is reported.
            if verbose and rule is not None:
                any_match = True
                _emit_verbose(rule, token, base_root=base_root, zero=zero, out=out)
            elif ignored:
                any_match = True
                emit(token, zero=zero, out=out)
        out.flush()
    except BrokenPipeError:
        silence_broken_pipe()
        raise SystemExit(ExitCode.BROKEN_PIPE) from None

    raise SystemExit(ExitCode.SUCCESS if any_match else ExitCode.GENERAL_ERROR)


__all__ = ["cli_check"]
