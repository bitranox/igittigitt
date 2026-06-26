# BMK MAKEFILE 2.9.5
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
# On every invocation, bmk is (re-)installed as a persistent uv tool
# together with the current project's dependencies (read from ./pyproject.toml).
# This ensures pyright, pytest, pip-audit etc. can resolve the full
# dependency tree without PYTHONPATH hacks or a local .venv.
#
# Arguments after the target name are forwarded automatically.
# You can also use ARGS="..." explicitly if preferred.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Use absolute path to the uv tool binary so active virtualenvs cannot shadow it.
BMK := $(HOME)/.local/bin/bmk
ARGS ?=

# ──────────────────────────────────────────────────────────────
# Ensure bmk + project deps are installed as a persistent uv tool
# ──────────────────────────────────────────────────────────────
# --reinstall re-resolves deps on every call (fast when cached).
# Fallback handles first-time install where --reinstall would fail.
.PHONY: _ensure_bmk
_ensure_bmk:
	@uv tool install --reinstall bmk --with . 2>/dev/null || uv tool install bmk --with .

# ──────────────────────────────────────────────────────────────
# Argument forwarding via MAKECMDGOALS
# ──────────────────────────────────────────────────────────────
# Allows natural argument passing: make push fix login bug
# instead of: make push ARGS="fix login bug"

# All targets that accept trailing arguments
_BMK_TARGETS := test t test-human th testintegration testi ti testintegration-human tih \
	codecov coverage cov \
	build bld clean cln cl run \
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
