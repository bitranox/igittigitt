# igittigitt

<!-- Badges -->
[![CI](https://github.com/bitranox/igittigitt/actions/workflows/default_cicd_public.yml/badge.svg)](https://github.com/bitranox/igittigitt/actions/workflows/default_cicd_public.yml)
[![CodeQL](https://github.com/bitranox/igittigitt/actions/workflows/codeql.yml/badge.svg)](https://github.com/bitranox/igittigitt/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open in Codespaces](https://img.shields.io/badge/Codespaces-Open-blue?logo=github&logoColor=white&style=flat-square)](https://codespaces.new/bitranox/igittigitt?quickstart=1)
[![PyPI](https://img.shields.io/pypi/v/igittigitt.svg)](https://pypi.org/project/igittigitt/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/igittigitt.svg)](https://pypi.org/project/igittigitt/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-46A3FF?logo=ruff&labelColor=000)](https://docs.astral.sh/ruff/)
[![codecov](https://codecov.io/gh/bitranox/igittigitt/graph/badge.svg?token=UFBaUDIgRk)](https://codecov.io/gh/bitranox/igittigitt)
[![Maintainability](https://qlty.sh/badges/041ba2c1-37d6-40bb-85a0-ec5a8a0aca0c/maintainability.svg)](https://qlty.sh/gh/bitranox/projects/igittigitt)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

`igittigitt` is a spec-compliant `.gitignore` parser for Python - a library **and** a
command-line tool. Point it at `.gitignore` rules (or pass rules as strings) and ask
whether a path is ignored, or use it directly as the `ignore=` callback of
`shutil.copytree`.

## Features

- **100% git-compatible matching.** The matching engine reproduces git's algorithm
  exactly - a single ordered pass with *last-matching-pattern-wins*, correct
  **negations** (`!pattern`), the rule that a file cannot be re-included when a parent
  directory is excluded, per-directory `.gitignore` precedence, anchors, trailing-slash
  (directory-only), `**`, `*`, `?` and `[...]` character classes. Compatibility is
  proven by a differential test suite that compares igittigitt against real `git
  check-ignore` on hundreds of generated cases. *(This fixes the negation and
  nested-precedence limitations of older releases.)*
- **Include / whitelist mode.** [`IncludeParser`](#whitelist--include-mode) inverts the
  logic: patterns describe what to **keep**. It is directory-aware (rsync-like), so it
  works correctly as a `copytree` filter even for deeply nested includes.
- **Memory-safe for millions of files.** Both modes stream per directory and decide each
  path in `O(depth x rules)`. Memory scales with the number of *rules*, never with the
  number of files or directories - so it stays flat on trees with millions of entries.
- **Scriptable CLI with piping.** `igittigitt check` mirrors `git check-ignore`, and
  `igittigitt filter` is a Unix filter that reads paths from stdin and prints the
  survivors - newline- or NUL-separated (`-z`), streamed, with clean SIGPIPE handling, so
  it drops cleanly into `find ... | igittigitt filter`.
- **Typed library, pure Python.** Ships `py.typed`, no runtime dependency on the `git`
  binary.

---

## Install

[uv](https://docs.astral.sh/uv/) is the recommended installer.

```bash
# as a project dependency
uv add igittigitt

# as a standalone CLI tool (isolated environment, added to PATH)
uv tool install igittigitt

# run once without installing
uvx igittigitt --help

# or classic pip / pipx
pip install igittigitt
pipx install igittigitt
```

The project targets **Python 3.10+** and is tested on Linux, macOS and Windows across
CPython 3.10-3.14. See [INSTALL.md](INSTALL.md) for every install method.

---

## Library usage

### Ignore mode

```python
import igittigitt

parser = igittigitt.IgnoreParser()

# discover and parse every .gitignore below base_dir (per-directory precedence)
parser.parse_rule_files(base_dir="/home/user/project")

# ... or add rules explicitly
parser.add_rule("*.py[cod]", base_path="/home/user/project")
parser.add_rule("!keep.pyc", base_path="/home/user/project")

parser.match("/home/user/project/main.pyc")   # True  (ignored)
parser.match("/home/user/project/keep.pyc")   # False (re-included by the negation)
```

Use it as a `shutil.copytree` filter to copy a tree without the ignored files:

```python
import shutil, igittigitt

parser = igittigitt.IgnoreParser()
parser.parse_rule_files(base_dir="src_tree")
shutil.copytree("src_tree", "dst_tree", ignore=parser.shutil_ignore)
```

### Whitelist / include mode

`IncludeParser` keeps only what matches; everything else is dropped. Including a
directory keeps its whole subtree, and unanchored patterns are found at any depth:

```python
import shutil, igittigitt

inc = igittigitt.IncludeParser()
inc.add_rule("*.py", base_path="src_tree")          # keep only python files...
inc.add_rule("docs/", base_path="src_tree")         # ...and the whole docs/ subtree

# copy only the kept files (parent directories are descended into automatically)
shutil.copytree("src_tree", "dst_tree", ignore=inc.shutil_include)

inc.match("src_tree/pkg/deep.py")                   # True  (kept)
```

---

## CLI usage

```bash
# which of these paths are ignored? (like `git check-ignore`)
igittigitt check -C /path/to/repo a.log src/main.py
#   exit 0 if at least one path is ignored, 1 if none

# show the matching rule (source:line:pattern), like `git check-ignore -v`
igittigitt check -C /path/to/repo -v a.log

# Unix filter: drop ignored paths from a stream
find . -type f | igittigitt filter

# keep only what matches the include patterns
find . -type f | igittigitt filter --include -r '*.py'

# NUL-separated I/O for paths with spaces/newlines
find . -print0 | igittigitt filter -z | xargs -0 ...

# inline rules and explicit ignore files
igittigitt check -r '*.tmp' -f .gitignore --stdin < paths.txt
```

### Global options

| Option                         | Description                                                                           |
|--------------------------------|---------------------------------------------------------------------------------------|
| `--version`                    | Print the version and exit.                                                           |
| `--traceback / --no-traceback` | Show a full Python traceback on errors (default: off).                                |
| `--profile NAME`               | Load configuration from a named profile.                                              |
| `--set SECTION.KEY=VALUE`      | Override one config value (repeatable), e.g. `--set performance.dir_cache_max=16384`. |
| `--env-file PATH`              | Use an explicit `.env` file (skips the upward search).                                |
| `-h, --help`                   | Show help.                                                                            |

### Commands

| Command                    | What it does                                                                                                                         |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `info`                     | Print resolved package metadata.                                                                                                     |
| `check [PATHS...]`         | Print the paths that are ignored (mirrors `git check-ignore`). Reads stdin with `--stdin`/`-`. Exit `0` if any matched, `1` if none. |
| `filter`                   | Unix filter: read paths from stdin and print the survivors. `--include` switches to whitelist mode.                                  |
| `config`                   | Print the merged, layered configuration (with provenance).                                                                           |
| `config-deploy`            | Write the default config files into the app/host/user config directories.                                                            |
| `config-generate-examples` | Write example config files you can copy and edit.                                                                                    |
| `logdemo`                  | Emit sample log records (handy to preview logging themes).                                                                           |

Shared `check` / `filter` options: `-C/--base-dir`, `-f/--gitignore FILE` (repeatable),
`-r/--rule PATTERN` (repeatable), `--scan/--no-scan`, `--default-patterns`, `-z/--zero`
(NUL I/O), and (`check` only) `-v/--verbose` and `--stdin`.

`check` and `filter` stream their input and write results immediately, with clean
`SIGPIPE` handling - so `... | igittigitt filter | head` works without errors.

---

## Configuration

igittigitt uses [lib_layered_config](https://github.com/bitranox/lib_layered_config):
settings are merged from, lowest to highest precedence,

```
bundled defaults -> app -> host -> user -> .env file -> environment variables -> --set
```

Inspect the effective configuration with `igittigitt config`, and deploy editable copies
with `igittigitt config-deploy`. Override a single value per run with `--set`, in a `.env`
file as `SECTION__KEY=value`, or via an environment variable as `IGITTIGITT___SECTION__KEY=value`.

### `[performance]` - engine and CLI tuning

These knobs only affect speed and cache memory, never which paths match. Defaults were
chosen by measurement; all keep memory bounded.

| Key                 | Default   | Meaning                                                                                                                                                      |
|---------------------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dir_cache_max`     | `8192`    | Capacity of the per-parser directory-decision LRU cache (`0` disables it). The main speed-up on tree-shaped workloads; memory is `O(this)`, not `O(#files)`. |
| `pattern_cache_max` | `4096`    | Capacity of the process-wide compiled-regex cache (keyed by distinct pattern).                                                                               |
| `stdin_chunk_bytes` | `65536`   | Read granularity for streaming paths from stdin.                                                                                                             |
| `max_token_bytes`   | `1048576` | Per-path safety bound; a separator-less token larger than this is rejected instead of buffered unbounded.                                                    |

Example: `igittigitt --set performance.dir_cache_max=32768 filter -C repo`.

### `[lib_log_rich]` - logging

Logging is provided by [lib_log_rich](https://github.com/bitranox/lib_log_rich). The
`[lib_log_rich]` section configures console level/theme, journald/eventlog/Graylog
backends, queueing, scrubbing and payload limits. Every key is documented inline in the
deployed `config.d/90-logging.toml`; for example set the console level with
`igittigitt --set lib_log_rich.console_level=DEBUG info` or
`IGITTIGITT___LIB_LOG_RICH__CONSOLE_LEVEL=DEBUG`.

The full, commented settings live in the bundled config files (see `config-generate-examples`)
and in [CONFIG.md](CONFIG.md).

---

## Claude Code skill

This repo is itself a [Claude Code](https://docs.claude.com/en/docs/claude-code)
plugin/marketplace and ships a skill ([`skills/python-gitignore/`](skills/python-gitignore/SKILL.md))
that teaches Claude how to install, configure and use igittigitt (library, CLI, and bash
piping). Install it in any project:

```text
/plugin marketplace add bitranox/igittigitt
/plugin install igittigitt
```

The same skill is also mirrored in the central bitranox marketplace
(<https://github.com/bitranox/bitranox-skills>) as `python-gitignore`.

---

## AI transparency

This project was built by a human with AI assistance, used as a tool under human direction.

- [ai-stance.md](ai-stance.md) - why we work this way and how we think about AI in software.
- [ai-disclosure.md](ai-disclosure.md) - exactly where AI was and was not used in this project,
  and what has and has not been tested.

---

## Further Documentation

- [INSTALL.md](INSTALL.md) - every installation method.
- [DEVELOPMENT.md](DEVELOPMENT.md) - make targets, testing, release workflow.
- [CHANGELOG.md](CHANGELOG.md) - release history.
- [CONTRIBUTING.md](CONTRIBUTING.md) - how to contribute.
