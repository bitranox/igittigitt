# Module Reference

## Core engine - `igittigitt/igittigitt.py`

The whole matching engine lives here (pure Python, no dependency on the `git` binary).

- `IgnoreParser` - parse `.gitignore` rules (`parse_rule_files`, `parse_rule_file`,
  `add_rule`, `load_default_patterns`) and query paths (`match`, `match_with_rule`).
  Use `shutil_ignore` as the `ignore=` callback of `shutil.copytree`.
- `IncludeParser` - the inverse include / whitelist mode (directory-aware). Use
  `shutil_include` as the `copytree` filter.
- `IgnoreRule` - a slotted `@dataclass` holding one compiled rule.
- Pattern-translation helpers: `get_rules_from_git_pattern`, `collapse_asterisk_runs`,
  `git_pattern_handle_blanks`, `get_match_anchored`, `get_match_files`,
  `create_rule_variations`.

### Runs of asterisks

git's wildmatch treats any run of two or more asterisks that fills a whole path segment
as `**`. `collapse_asterisk_runs` rewrites such a segment (`***`, `****`, ...) to `**`
before the leading `**/` and trailing `/**` forms are handled, so `***/build`,
`a/****/b` and `logs/***` take the same path as their `**` spellings. A run inside a
longer segment is left alone: `a***b` behaves like `a*b` and never crosses a `/`.

### Matching algorithm (git-faithful)

Rules are kept in a single ordered list (per directory by depth, then by line). A path is
evaluated by walking it top-down: if an ancestor directory is excluded (and not
re-included at its own level) the path is ignored and cannot be re-included; otherwise the
path's own last-matching rule decides. Directory exclusion therefore cascades to the whole
subtree without storing per-file state, keeping memory `O(rules)` and per-path work
`O(depth x rules)`.

Compatibility is verified against real `git check-ignore` in `tests/test_git_compat.py`.

## Configuration - `igittigitt/conf_igittigitt.py`

`ConfIgittIgitt` (a `pydantic` model) holds runtime options, currently
`add_default_patterns`. The module-level `conf_igittigitt` instance provides the defaults.

## Metadata - `igittigitt/__init__conf__.py`

Static package metadata constants and `print_info()` (used by the CLI `info` command),
kept in sync with `pyproject.toml`.

## CLI - `igittigitt/adapters/cli/`

A rich-click application (adapter layer) that depends only on the core engine.

- `root.py` - the root group with `--version` / `--traceback`.
- `config_load.py` - loads the layered configuration for the root group and records a load
  failure instead of raising it; `require_config` refuses a command that reads a configuration
  that did not load with exit 78 (`config`, `check`, `filter`), while `info`, `config-deploy`,
  `config-generate-examples`, `logdemo` and help still run. A malformed or conflicting `--set` and an
  invalid `--profile` name are usage errors (exit 2), checked before loading.
- `main.py` / `entry.py` / `__main__.py` - entry points with a `lib_cli_exit_tools` error
  boundary.
- `exit_codes.py` - the POSIX `ExitCode` enum (including `BROKEN_PIPE = 141`).
- `commands/info.py` - `info`.
- `commands/check.py` - `check`, mirroring `git check-ignore`; `-v` reports the deciding rule
  (negations included) with the rule file relative to `--base-dir`, and `-v -z` NUL-terminates
  each field, as git does. `tests/test_git_compat.py` compares both forms with real git.
- `commands/filter.py` - `filter`, a streaming Unix filter (stdin, `-z`, ignore/include).
- `commands/_common.py` - shared streaming/parser-building helpers (bounded memory).
