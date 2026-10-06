# Changelog

All notable changes to this project will be documented in this file following
the [Keep a Changelog](https://keepachangelog.com/) format.

This project adheres to semantic versioning: MAJOR for incompatible API changes,
MINOR for backwards-compatible functionality, PATCH for backwards-compatible fixes.

## [Unreleased]

### Fixed

- **`build_testing()` can run a command.** Every CLI command except `check` and `filter` binds job
  context onto the process-global lib_log_rich runtime, but the testing composition's
  `init_logging` was a no-op, so `info`, `config` and the deploy commands raised
  `RuntimeError('lib_log_rich.init() must be called before using the logging API')` under
  `build_testing()`. The in-memory initializer now starts a quiet runtime: journald, event log,
  Graylog and the queue off, console at ERROR, and no `.env` loading.
- **`main()` keeps the exit code of a command that exits through click's context.** rich_click's
  `main()` returns the code of a `ctx.exit(N)` under `standalone_mode=False`; `main()` discarded
  that return value and reported 0, and its `except click.exceptions.Exit` branch could never
  fire. It now returns the code (exit code change: such a command exits N instead of 0).
- **Conflicting `--set` overrides are a usage error.** `--set a.b=1 --set a.b.c=2` escaped as a
  `TypeError` from the override nesting, and the other order, `--set a.b.c=2 --set a.b=1`,
  silently dropped the earlier override. All `--set` values are now checked together and a key
  that one gives a value and another puts a key under is refused, naming both (exit code change:
  exit 2 for every command, where the second order used to exit 0). The same key given twice still
  takes the last value; `a.b` and `a.bc` stay siblings.
- **A broken configuration file no longer disables every command.** The root group loaded the
  configuration before any subcommand option was parsed and let a load error escape, so a
  malformed `config.toml`, a `.env` that is not UTF-8 or an unreadable file made every command,
  `--help` and `config-deploy` (the command that replaces the file) exit 1. The root now records
  the failure (`adapters/cli/config_load.py`): `config`, `check` and `filter`, which read the
  configuration, refuse with exit 78 and one line naming the file, after the loader's traceback
  with `--traceback`; `info`, `config-deploy`, `config-generate-examples` and help still run
  (exit code change: 78 or 0 where every command exited 1). What the command line gets wrong is
  checked before loading, so a broken file cannot hide it: a malformed or conflicting `--set` or
  an invalid `--profile` name is a usage error (exit 2) for every command, where an invalid
  root `--profile` used to exit 22 and an invalid `config-deploy --profile` failed inside the
  deploy with exit 1. Any other exception from the loader is a bug and propagates as one.
  `config --profile X` reloads with the root's `--env-file` instead of searching for another
  `.env`.
- **Logging takes only `LOG_*` lines from a `.env`.** `init_logging` called lib_log_rich's
  `enable_dotenv()`, which copied every line of the nearest `.env` into the process environment,
  so a later configuration load (`config --profile`, the deploy's permission read) took an
  app-prefixed `.env` line for the environment layer: a prefixed `default_permissions` line in the
  working directory's `.env` refused `config-deploy`, and a prefixed `[performance]` value showed
  up in `config --profile`. Logging now copies only `LOG_*` lines, never over a variable that is
  already set, from `--env-file` when given, otherwise from the nearest `.env` up to the project
  root, without `chdir` and passing over unreadable directories; a `.env` that is not UTF-8 no
  longer stops logging.
- **An invalid `[lib_log_rich]` value is a configuration failure, not a crash of every command.**
  A value lib_log_rich refuses (a wrong type, or its own range checks such as `queue_maxsize = 0`)
  stopped every command with exit 22 and pydantic's multi-line report. It is now recorded like a load
  failure: logging starts with its defaults, `config`, `check` and `filter` exit 78 with one
  `Error:` line per problem naming the key, never the value, and `info`, `config-deploy` and help
  run (exit code change). The `InitLogging` port takes `dotenv_path`, and the root types the
  services factory instead of ignoring the type.
- **`config-deploy` leaves every permission decision to lib_layered_config.** The command read
  `[lib_layered_config.default_permissions]` from its own merged configuration, so a `.env` found
  upward from the working directory decided or blocked a system deploy, and of the whole section
  only `enabled` was ever used: the configured per-layer modes never reached a deploy, and a
  section that was not a table crashed with `AttributeError`. It now passes its options and any
  `--set` of that section to `deploy_config` unchanged; the library reads the section from the
  bundled defaults, the files the deploy does not overwrite and the environment, never from
  `.env`, and applies each target's own layer modes. A refused setting exits 78 with one `Error:`
  line per problem naming the key and its source, plus a hint in the CLI's spelling when both mode
  options would get past it (exit code change: 78 where an invalid section used to exit 1 or
  deploy). "Deployed configuration" is logged after the deploy, and the report says
  "(permissions not set)" only for an explicit `--no-permissions`.
- **Tests no longer depend on test order, colour or terminal width.** An autouse fixture shuts the
  logging runtime down and restores the root logger's handlers, level and propagate flag after
  every test (production `init_logging` attaches a stdlib handler and raises the root level, which
  `runtime.shutdown()` does not undo). A second one pins rich-click's colour and width globals,
  which it reads from the terminal and from GITHUB_ACTIONS once at import, so a usage-error box
  no longer wraps a message the test looks for on a narrow terminal.

### Changed

- **Requires lib_layered_config 7.0.1**, whose `deploy_config` reads and validates the permission
  section itself. An unquoted `.env` value now converts like the environment layer, so
  `ENABLED=false` arrives as the boolean `false`.
- **`--no-permissions` together with `--dir-mode` or `--file-mode` is a usage error** (exit 2):
  a mode cannot be applied while permission setting is off.
- **`python-dotenv` is a declared dependency** (logging reads the `LOG_*` lines of a `.env` with
  it), and lib_log_rich is required at 6.3.9, the version the logging refusal is tested against.
- **`click` is a declared dependency.** The package imports it directly (`adapters/cli/main.py`)
  but only had it through rich-click. A new test fails when a module imported at run time is
  missing from `[project].dependencies`.

### Removed

- `adapters.config.permissions` (`PermissionDefaults`, `parse_mode`, `get_permission_defaults`,
  `get_modes_for_target`): lib_layered_config reads and validates the section now. `parse_mode`
  silently fell back to the default on a malformed value, and `get_modes_for_target` had no
  production caller, which is why the configured modes never took effect.

### Security

- **`config-deploy` refuses unsafe and malformed modes.** `--dir-mode -1` passed the unbounded
  octal parser and reached the deploy as mode -1, and `--dir-mode 777` or `--file-mode 666` were
  applied as given. `--dir-mode`/`--file-mode` and the configured modes are now parsed by
  lib_layered_config's `DeployMode`: only a plain octal literal inside 0..0o7777 is accepted, and
  setuid/setgid/sticky, group or world write, an execute bit on a file and a mode that takes away
  the owner's access are refused (exit 2 for an option, 78 for a configured value). A bare integer
  in the configuration is refused because it is read as decimal (`400` is `0o620`).

## [2.2.3] 2026-07-30 18:08:55

### Changed

- **The shipped skill's plugin version now tracks the package version.** bmk 3.14.0 raises
  `.claude-plugin/plugin.json` to the package version on bump, push and release, and never lowers
  it. An install re-fetches a skill only when that version changes, so the two numbers drifting
  apart meant a skill edit could ship to nobody. No functional change to the library.

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
