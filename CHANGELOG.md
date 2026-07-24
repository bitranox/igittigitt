# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.

This project adheres to semantic versioning: MAJOR for incompatible API changes,
MINOR for backwards-compatible functionality, PATCH for backwards-compatible fixes.

## [Unreleased]

## [2.2.2] 2026-07-24 18:15:33

### Fixed
- Latest `ruff` (0.16+) widened default rule coverage; the project's curated
  `[tool.ruff.lint]` blanket ignore list (`RUF002`, `RUF022`, `PLC0415`, `TC001-3`,
  `TC006`) is removed and every violation it was masking is fixed at the root
  instead: keyword-only params on the six flagged Click callbacks/helpers
  (`build_ignore_parser`, `cli_check`, `cli_filter`, `cli_config_deploy`,
  `_execute_deploy`, `create_rule_variations`) rather than adding rule
  suppressions, an ASCII hyphen in place of an ambiguous en-dash in a docstring,
  and top-level (rather than deferred) imports where no circular-import or
  lazy-load reason applied. A doctest in `adapters/config/permissions.py` that
  relied on `DeployTarget` moving out of `TYPE_CHECKING` is made self-contained.
- Deferred imports in `tests/*.py` are now a declared per-file ignore
  (`PLC0415`) rather than silently unflagged - they are a deliberate test idiom
  (exercising import/cache behaviour), not an oversight.

### Changed
- CI (template-managed, from `default_cicd_public`): `pip-audit` now audits this
  project's own resolved dependency tree instead of the whole `--system`
  environment, so runner-image packages we neither declare nor ship (`setuptools`,
  `pip`, `wheel`) can no longer report findings against us. `actions/cache` moves
  to v6 in the same distribution.
- Dev dependency floor: `httpx2>=2.7.0` (was `>=2.6.0`).
- `[tool.ruff.lint.flake8-type-checking].runtime-evaluated-base-classes` now
  lists `pydantic.BaseModel`, so the `TC00x` autofix leaves Pydantic model base
  classes importable at runtime instead of moving them into `TYPE_CHECKING`.
- `skills/python-gitignore/SKILL.md` example code blocks reformatted to match
  ruff's latest formatting (cosmetic only; no semantic change to the skill).
  `.claude-plugin/plugin.json` bumped to `1.0.1` to ship the change.

## [2.2.1] - 2026-07-14

A maintenance release: no library or CLI behaviour changes beyond the profile
validation fix below. The public API is unchanged.

### Fixed
- `validate_profile()` raises `ValueError` for every invalid profile again. Newer
  `lib_layered_config` raises its own `ValidationError`, which escaped the
  documented `ValueError` contract and slipped past callers' `except ValueError`
  guards; the dependency's exception is now normalised back to `ValueError`.
- Pyright strict passes against click 8.3+. The `argument` decorator's re-exported
  signature carries an unknown `type` parameter, so it joins `option` and
  `version_option` behind a fully-typed wrapper in `adapters/cli/typed_click`
  instead of the rule being disabled.

### Documentation
- `ExitCode`'s docstring no longer claims the application never exits with a
  signal code. `BROKEN_PIPE` (141) is raised directly by `check` and `filter` when
  their output pipe closes early; only 130 and 143 are informational.
- `INSTALL.md`: the install-from-tag example pointed at `v1.1.0`, a tag that was
  never cut, and the closing line named the installed command twice. Both fixed.

### Changed
- `codecov-cli` is disabled as a dev dependency. It pins `click<8.3.0`, which both
  held click at a version with a known `click.edit()` command-injection flaw and
  silently backtracked `bmk` to 3.1.7. CI uploads coverage via
  `codecov/codecov-action`, so nothing is lost.
- The bmk-managed `Makefile` regenerates at 3.6.0 (from 2.9.5), and bmk now lives
  in a per-project `.venv-bmk` tool environment rather than a shared one. This is
  the first bmk update the repo has picked up since the `click` pin was removed.
- The `[tool.pip-audit]` ignore list is now empty. Every entry it carried had
  become inert (fixed upstream, or naming a package absent from the dependency
  tree), and a stale entry silently suppresses any future advisory filed under the
  same id.

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
