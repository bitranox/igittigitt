# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.

This project adheres to semantic versioning: MAJOR for incompatible API changes,
MINOR for backwards-compatible functionality, PATCH for backwards-compatible fixes.

## [Unreleased]

## [2.2.0] - 2026-06-26

Full rebuild of the project scaffolding on the `bitranox_template_py_cli` template
(src layout, hatchling, ruff + pyright strict, clean-architecture CLI). The public
library API (`import igittigitt; igittigitt.IgnoreParser`) is unchanged.

### Added
- **`IncludeParser`** - a directory-aware include / whitelist mode with
  `shutil_include` for use as a `shutil.copytree` filter.
- **Scriptable CLI** built on rich-click: `check` (mirrors `git check-ignore`,
  including `-v`) and `filter` (a streaming Unix filter reading paths from stdin),
  with newline- or NUL-separated (`-z`) I/O and clean SIGPIPE handling. Plus
  `info`, `config`, `config-deploy`, `config-generate-examples` and `logdemo`.
- **Layered configuration** (`lib_layered_config`) and **structured logging**
  (`lib_log_rich`). All engine/CLI tuning knobs are exposed and documented in the
  `[performance]` config section (`dir_cache_max`, `pattern_cache_max`,
  `stdin_chunk_bytes`, `max_token_bytes`) and overridable via file / `.env` / env
  var / `--set`.
- Differential test suite comparing igittigitt against real `git check-ignore`,
  plus memory-boundedness, include, config-knob and real-pipe/SIGPIPE tests.

### Changed
- **Matching is now 100% git-compatible.** The engine performs a single ordered
  pass (last-matching-pattern-wins) with correct negations, parent-directory
  exclusion blocking re-inclusion, and per-directory `.gitignore` precedence. This
  resolves the long-standing negation and nested-precedence limitations.
- Matching is memory-bounded: per-path cost is `O(depth x rules)` and memory scales
  with the number of rules, not the number of files.
- Matching is ~5x faster: globs are translated and compiled to `re.Pattern` once
  (cached), and the ancestor-directory decision is memoized in a bounded LRU - both
  keep memory bounded and preserve 100% git compatibility.
- Dropped the `attrs` runtime dependency in favour of `dataclasses` and `pydantic`.
- Python baseline raised to **3.10+** (was 3.8).
- CLI migrated from `click` to `rich-click` with `lib_cli_exit_tools`.
- Documentation moved from reStructuredText to Markdown.

### Removed
- The old two-phase (sort-and-deduplicate) rule evaluation that broke negations.

## [2.1.5] - 2024-10-16
- Final release on the previous (PizzaCutter / setuptools-scm) scaffolding.
- Earlier history: a spec-compliant gitignore parser whose negation and nested
  precedence handling was known to be incomplete (see this release's README).
