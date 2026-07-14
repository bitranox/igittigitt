# BMK MAKEFILE 3.6.0
# do not alter this file - it might be overwritten on new versions of BMK
# if You want to alter it, remove the first line # BMK MAKEFILE 1.0 - then it is a custom makefile and will not be overwritten
# bmk Makefile — thin wrapper using `uv tool install` for persistent bmk
#
# Usage:
#   make test                        # run test suite
#   make test --verbose              # forward extra flags
#   make bump-patch                  # bump patch version
#   make push fix login bug          # push with commit message
#   make custom deploy                # run custom command
#   make custom deploy --dry-run
#
# bmk is installed into THIS PROJECT's own tool env (.venv-bmk) together with the
# project's dependencies (read from ./pyproject.toml), so pyright, pytest,
# pip-audit etc. resolve the full dependency tree without PYTHONPATH hacks. The
# env belongs to this repo alone, so projects cannot overwrite each other's
# dependencies. It is re-resolved on every invocation, so a new bmk release and any
# dependency change are picked up automatically.
#
# .venv-bmk is disposable - delete it and the next make rebuilds it.
#
# Arguments after the target name are forwarded automatically.
# You can also use ARGS="..." explicitly if preferred.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# uv names the executable bmk.exe on Windows.
ifeq ($(OS),Windows_NT)
  BMK_EXE := .exe
else
  BMK_EXE :=
endif

# bmk lives in a venv OF THIS PROJECT, not in a machine-wide one. The tool env
# holds bmk's toolchain PLUS this project's dependencies, so a single
# shared env cannot serve two projects: whichever ran `make` last wins, and the
# other silently gets the wrong dependency tree. Per-project is the only layout
# where "the env is correct" is a question about THIS repo alone.
BMK_TOOL_DIR := $(CURDIR)/.venv-bmk
BMK := $(BMK_TOOL_DIR)/bin/bmk$(BMK_EXE)
ARGS ?=

# ──────────────────────────────────────────────────────────────
# Ensure bmk + project deps are installed in this project's tool env
# ──────────────────────────────────────────────────────────────
# This runs before EVERY target, on purpose. `uv tool install --reinstall bmk`
# re-resolves the unpinned `bmk` spec against PyPI, so each make picks up a new bmk
# release and any change to this project's dependencies, with nothing to remember and
# no version marker to go stale. It costs a couple of seconds per invocation; that is
# the price of never running against a bmk or a dependency tree that has quietly
# drifted, and it is cheap next to a wrong test result.
#
# Every part of the recipe is load-bearing. Do not:
#
#   * drop `.[dev]` from either attempt, or add a `|| --with .` fallback. A project
#     with no [dev] extra does not fail here - uv warns and installs the base deps -
#     so such a fallback can only ever produce an env WITHOUT the test deps, which
#     surfaces as a ModuleNotFoundError (hypothesis, starlette.testclient) far from
#     the install that caused it.
#   * change `--with-editable` to `--with`. Editable keeps the project's code in the
#     env identical to the working tree. A non-editable `--with .` installs a SNAPSHOT;
#     it happens to work because tools run with cwd=<project>, whose source shadows the
#     snapshot on sys.path, but that is a coincidence of import order and would serve
#     stale code to anything running from another directory.
#   * drop `--reinstall` from either attempt. `uv tool install` without it NO-OPS when
#     the tool is already present, ignoring `--with` and the available version
#     entirely, and keeps a stale env.
#   * drop `--force`. The entry points exist in this project's bin dir on every rebuild.
#   * add `2>/dev/null`. A real failure must reach the terminal; a suppressed one
#     surfaces later, somewhere unrelated.
#   * collapse the retry. It covers the transient __pycache__ removal race
#     ("Directory not empty", os error 39). If BOTH attempts fail, make fails loudly -
#     correct, because there is no safe degraded state to continue from.
#   * drop the FLOOR from `bmk>=$(BMK_MIN)`. bmk and the project's deps resolve TOGETHER,
#     so a project dependency that caps something bmk requires does not fail - uv simply
#     backtracks BMK to an older release that fits, silently. That is not hypothetical:
#     `codecov-cli` caps click<8.3.0 while bmk requires click>=8.4.2 (CVE-2026-7246), so an
#     unpinned `bmk` resolves to 3.1.7 and the repo never sees another bmk update, with no
#     error at all. The floor turns that into an unsatisfiable-requirements error that names
#     the offending package. If it fires, remove the capping dependency - do not lower the
#     floor, or you are back to a silently ancient bmk.
BMK_MIN := 3.6.0

.PHONY: _ensure_bmk
_ensure_bmk:
	@UV_TOOL_DIR="$(BMK_TOOL_DIR)" UV_TOOL_BIN_DIR="$(BMK_TOOL_DIR)/bin" \
	  uv tool install --reinstall --force "bmk>=$(BMK_MIN)" --with-editable ".[dev]" \
	  || UV_TOOL_DIR="$(BMK_TOOL_DIR)" UV_TOOL_BIN_DIR="$(BMK_TOOL_DIR)/bin" \
	  uv tool install --reinstall --force "bmk>=$(BMK_MIN)" --with-editable ".[dev]"

# ──────────────────────────────────────────────────────────────
# Argument forwarding via MAKECMDGOALS
# ──────────────────────────────────────────────────────────────
# Allows natural argument passing: make push fix login bug
# instead of: make push ARGS="fix login bug"

# All targets that accept trailing arguments
_BMK_TARGETS := test t test-human th testintegration testi ti testintegration-human tih \
	codecov coverage cov \
	build bld clean cln cl run ensure \
	bump-major bump-minor bump-patch bump \
	commit c push psh p release rel r ship sh \
	dependencies deps d dependencies-update \
	config config-deploy config-generate-examples \
	send-email send-notification custom \
	info logdemo

ifneq (,$(filter $(_BMK_TARGETS),$(firstword $(MAKECMDGOALS))))
  # Capture everything after the first word as extra arguments
  _EXTRA := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # Append to ARGS (so explicit ARGS="..." still works alongside)
  override ARGS += $(_EXTRA)
endif

# ──────────────────────────────────────────────────────────────
# Test & Quality
# ──────────────────────────────────────────────────────────────

.PHONY: test t
test: _ensure_bmk  ## Run test suite [alias: t]
	$(BMK) test $(ARGS)
t: _ensure_bmk
	$(BMK) test $(ARGS)

.PHONY: test-human th
test-human: _ensure_bmk  ## Run test suite with human-readable output [alias: th]
	$(BMK) test --human $(ARGS)
th: _ensure_bmk
	$(BMK) test --human $(ARGS)

.PHONY: testintegration testi ti
testintegration: _ensure_bmk  ## Run integration tests only [aliases: testi, ti]
	$(BMK) testintegration $(ARGS)
testi ti: _ensure_bmk
	$(BMK) testintegration $(ARGS)

.PHONY: testintegration-human tih
testintegration-human: _ensure_bmk  ## Run integration tests with human-readable output [alias: tih]
	$(BMK) testintegration --human $(ARGS)
tih: _ensure_bmk
	$(BMK) testintegration --human $(ARGS)

.PHONY: codecov coverage cov
codecov: _ensure_bmk  ## Upload coverage report to Codecov [aliases: coverage, cov]
	$(BMK) codecov $(ARGS)
coverage cov: _ensure_bmk
	$(BMK) codecov $(ARGS)

# ──────────────────────────────────────────────────────────────
# Build & Clean
# ──────────────────────────────────────────────────────────────

.PHONY: build bld
build: _ensure_bmk  ## Build wheel and sdist artifacts [alias: bld]
	$(BMK) build $(ARGS)
bld: _ensure_bmk
	$(BMK) build $(ARGS)

.PHONY: clean cln cl
clean: _ensure_bmk  ## Remove build artifacts and caches [aliases: cln, cl]
	$(BMK) clean $(ARGS)
cln cl: _ensure_bmk
	$(BMK) clean $(ARGS)

# ──────────────────────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────────────────────

.PHONY: run
run: _ensure_bmk  ## Run the project CLI
	$(BMK) run $(ARGS)

.PHONY: ensure
ensure: _ensure_bmk  ## Install missing external tools for this OS
	$(BMK) ensure $(ARGS)

# ──────────────────────────────────────────────────────────────
# Version Bumping
# ──────────────────────────────────────────────────────────────

.PHONY: bump-major
bump-major: _ensure_bmk  ## Bump major version (X+1).0.0
	$(BMK) bump major $(ARGS)

.PHONY: bump-minor
bump-minor: _ensure_bmk  ## Bump minor version X.(Y+1).0
	$(BMK) bump minor $(ARGS)

.PHONY: bump-patch
bump-patch: _ensure_bmk  ## Bump patch version X.Y.(Z+1)
	$(BMK) bump patch $(ARGS)

.PHONY: bump
bump: bump-patch  ## Bump patch version (default for bump)

# ──────────────────────────────────────────────────────────────
# Git Operations
# ──────────────────────────────────────────────────────────────

.PHONY: commit c
commit: _ensure_bmk  ## Create a git commit with timestamped message [alias: c]
	$(BMK) commit $(ARGS)
c: _ensure_bmk
	$(BMK) commit $(ARGS)

.PHONY: push psh p
push: _ensure_bmk  ## Run tests, commit, and push to remote [aliases: psh, p]
	$(BMK) push $(ARGS)
psh p: _ensure_bmk
	$(BMK) push $(ARGS)

.PHONY: release rel r
release: _ensure_bmk  ## Create a versioned release (tag + GitHub release) [aliases: rel, r]
	$(BMK) release $(ARGS)
rel r: _ensure_bmk
	$(BMK) release $(ARGS)

.PHONY: ship sh
ship: _ensure_bmk  ## Push, wait for CI, release, wait for release CI (CI-gated) [alias: sh]
	$(BMK) ship $(ARGS)
sh: _ensure_bmk
	$(BMK) ship $(ARGS)

# ──────────────────────────────────────────────────────────────
# Dependencies
# ──────────────────────────────────────────────────────────────

.PHONY: dependencies deps d
dependencies: _ensure_bmk  ## Check and list project dependencies [aliases: deps, d]
	$(BMK) dependencies $(ARGS)
deps d: _ensure_bmk
	$(BMK) dependencies $(ARGS)

.PHONY: dependencies-update
dependencies-update: _ensure_bmk  ## Update dependencies to latest versions
	$(BMK) dependencies update $(ARGS)

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

.PHONY: config
config: _ensure_bmk  ## Show current merged configuration
	$(BMK) config $(ARGS)

.PHONY: config-deploy
config-deploy: _ensure_bmk  ## Deploy configuration to system/user directories
	$(BMK) config-deploy $(ARGS)

.PHONY: config-generate-examples
config-generate-examples: _ensure_bmk  ## Generate example configuration files
	$(BMK) config-generate-examples $(ARGS)

# ──────────────────────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────────────────────

.PHONY: send-email
send-email: _ensure_bmk  ## Send an email via configured SMTP
	$(BMK) send-email $(ARGS)

.PHONY: send-notification
send-notification: _ensure_bmk  ## Send a plain-text notification email
	$(BMK) send-notification $(ARGS)

# ──────────────────────────────────────────────────────────────
# Custom Commands
# ──────────────────────────────────────────────────────────────

.PHONY: custom
custom: _ensure_bmk  ## Run a custom command (make custom <name> [args...])
	$(BMK) custom $(ARGS)

# ──────────────────────────────────────────────────────────────
# Info & Demos
# ──────────────────────────────────────────────────────────────

.PHONY: info
info: _ensure_bmk  ## Print resolved package metadata
	$(BMK) info $(ARGS)

.PHONY: logdemo
logdemo: _ensure_bmk  ## Run logging demonstration
	$(BMK) logdemo $(ARGS)

.PHONY: version-current
version-current: _ensure_bmk  ## Print current version
	$(BMK) --version

# ──────────────────────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────────────────────

.PHONY: dev
dev:  ## Install package with dev extras (editable)
	uv pip install -e ".[dev]"


.PHONY: install
install:  ## Editable install (no dev extras)
	uv pip install -e .

# ──────────────────────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────────────────────

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}' | \
		sort

# ──────────────────────────────────────────────────────────────
# No-op overrides for trailing argument words (MUST be last)
# ──────────────────────────────────────────────────────────────
# Placed after all real target definitions so the no-op recipes
# override them.  This prevents "make push codecov fix" from
# executing the real codecov target — "codecov" is an argument
# to push, not a separate command.
ifneq (,$(_EXTRA))
$(_EXTRA):
	@:
endif
