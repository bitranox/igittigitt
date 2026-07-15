# BMK MAKEFILE 3.9.0
# do not alter this file - it might be overwritten on new versions of BMK
# if You want to alter it, remove the first line # BMK MAKEFILE 1.0 - then it is a custom makefile and will not be overwritten
# bmk Makefile — thin wrapper using `uv tool install` for persistent bmk
#
# Usage:
#   make test                        # run test suite
#   make test ARGS="--verbose"       # forward extra FLAGS (bare --verbose would be parsed
#                                    #   by make itself, not forwarded: "unknown option")
#   make bump-patch                  # bump patch version
#   make push fix login bug          # push with a plain one-line commit message
#   make push MSG="fix(cli): x"      # push with ANY message: punctuation, newlines, $ - all safe
#   make custom deploy                # run custom command
#   make custom deploy --dry-run
#
# bmk is installed ONCE per machine, in uv's own tool dir, and holds NOTHING of this
# project: only bmk and its toolchain. Your project's dependencies live in the project's
# own venv (.venv), which bmk provisions and syncs from ./pyproject.toml, and that is the
# env your tests, pyright and pip-audit all run against.
#
# That separation is the point. bmk used to be installed together with the project's
# dependencies in one env that resolved them TOGETHER, and every consequence of that was
# a bug: a project dependency capping one of bmk's silently backtracked bmk to an ancient
# release; a yanked transitive dependency made bmk itself uninstallable, bricking `make`
# fleet-wide; and the tests ran in that co-resolved env while pyright and pip-audit
# inspected the project's real venv - so the suite and the audit described different
# environments. With no project dependencies in bmk's env, none of that can happen, and
# one shared env serves every repo (it is identical for all of them).
#
# The env is disposable - delete it and the next make rebuilds it. It is re-resolved on
# every invocation, so a new bmk release is picked up automatically.
#
# Arguments after the target name are forwarded automatically.
# You can also use ARGS="..." explicitly if preferred.
#
# For a COMMIT MESSAGE prefer MSG="..." over ARGS="..." - ARGS is re-parsed by bash, so
# punctuation like ( ) ; ` $ * breaks or executes, and a newline is impossible. See the
# "Commit messages" section below.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# uv names the executable bmk.exe on Windows.
ifeq ($(OS),Windows_NT)
  BMK_EXE := .exe
else
  BMK_EXE :=
endif

# ONE bmk per machine, in uv's own tool dir - not a copy per project.
#
# A per-project env was necessary only while the env also carried the PROJECT's
# dependencies: two projects then fought over one env, whichever ran `make` last winning
# (measured - a `six` project and a `chardet` project overwrote each other). bmk's env now
# holds bmk alone, so it is byte-identical for every repo and there is nothing left to
# collide. Sharing it costs nothing and stops ~300MB (mostly pyright's bundled Node) from
# being duplicated into all ~46 repos.
#
# Ask uv where it puts entry points rather than trusting PATH: `uv tool install` warns
# (and does nothing about it) when its bin dir is not on PATH, which is the default state
# on a fresh machine, and a bare `bmk` would then fail with "command not found" from a
# Makefile that had just installed it. Falling back to the bare name keeps the old
# behaviour if uv is too old to answer.
BMK_BIN_DIR := $(shell uv tool dir --bin 2>/dev/null)
BMK := $(if $(BMK_BIN_DIR),$(BMK_BIN_DIR)/bmk$(BMK_EXE),bmk$(BMK_EXE))
ARGS ?=

# ──────────────────────────────────────────────────────────────
# Commit messages: MSG= is the safe channel, ARGS= is not
# ──────────────────────────────────────────────────────────────
# A commit message is free-form PROSE, and prose does not survive a shell command line.
# make expands $(ARGS) into the recipe text and hands the RESULT to /bin/bash, which then
# applies its full grammar to words that were never escaped for it. The quotes you typed
# were eaten by your own shell long before make saw them. So a bare ARGS= message means
# bash parses your prose as code: "fix(cli): x" is a syntax error, "a; b" runs b, and a
# backtick or $(...) EXECUTES. A newline is the worst case - it ends the recipe LINE, so
# make commits a truncated subject on line 1 and then runs the rest as a command.
#
# MSG= avoids all of it by never touching a command line. make's `export` puts the value
# straight into the child process environment, where nothing is word-split or re-parsed,
# and bmk already prefers args -> BMK_COMMIT_MESSAGE -> prompt (git_ops.resolve_message).
# git commit -m accepts embedded newlines, so a MSG= body becomes a real commit body.
#
#   make push MSG="fix(cli): subject line
#
#   Body with (parens), a ; and a $HOME, all safe."
#
# $(value MSG) is deliberate: it yields the UNEXPANDED value, so a literal $ in the message
# survives. Plain $(MSG) would make-expand it first and silently turn $HOME into OME.
ifdef MSG
export BMK_COMMIT_MESSAGE := $(value MSG)
endif

# A newline in ARGS cannot be made safe (see above), so refuse it up front rather than
# commit half of it. $(error) fires during parsing, before any recipe runs, so nothing is
# staged, committed or pushed. This guard exists because the truncate-then-push failure is
# silent and has already shipped wrong commit messages more than once.
define _BMK_NEWLINE


endef
ifneq (,$(findstring $(_BMK_NEWLINE),$(ARGS)))
  $(error ARGS contains a newline, which make cannot pass to a recipe safely. Use MSG="..." for a multi-line commit message)
endif

# ──────────────────────────────────────────────────────────────
# Ensure bmk (and ONLY bmk) is installed, once per machine
# ──────────────────────────────────────────────────────────────
# This runs before EVERY target, on purpose: `--reinstall` re-resolves the `bmk` spec so
# each make picks up a new bmk release with nothing to remember and no version marker to
# go stale. It costs a couple of seconds; that is the price of never running against a bmk
# that has quietly drifted.
#
# `--reinstall` alone does NOT deliver that, which is why $(BMK_REFRESH) exists: uv
# re-resolves against its CACHED package index, so a release published minutes ago is
# invisible and you silently keep the old bmk until the cache revalidates (measured: with
# 3.8.0 on PyPI, `uv tool install "bmk>=3.7.1"` still installed 3.7.1). Refreshing just
# bmk's own metadata makes "picked up automatically" true immediately, for ~1s per make.
#
# NOTE what is NOT here: the project. bmk is installed on its own, so its env holds bmk's
# toolchain and nothing else. The project's dependencies live in the project's own venv
# (.venv), which bmk provisions from ./pyproject.toml and runs the tests, pyright and
# pip-audit against. Do NOT "restore" a `--with .` / `--with-editable ".[dev]"`: that is
# what made bmk and the project resolve TOGETHER, and it caused, in order - a project
# dependency capping one of bmk's silently backtracking bmk to an ancient release
# (codecov-cli capped click<8.3.0 against bmk's click>=8.4.2, pinning bmk at 3.1.7 with no
# error); a yanked transitive dependency making bmk itself uninstallable and bricking
# `make` in every repo; and the suite running in that co-resolved env while pyright and
# pip-audit inspected the project's real venv, so the tests and the audit described
# different environments. It also forced an env per project, duplicating ~300MB per repo.
#
# The rest of the recipe is load-bearing. Do not:
#
#   * drop `--reinstall` from either attempt. `uv tool install` without it NO-OPS when the
#     tool is already present, ignoring the available version entirely, and keeps a stale env.
#   * drop `--force`. The entry point already exists in uv's bin dir on every rebuild.
#   * add `2>/dev/null`. A real failure must reach the terminal; a suppressed one surfaces
#     later, somewhere unrelated.
#   * collapse the retry. It covers the transient __pycache__ removal race ("Directory not
#     empty", os error 39). If BOTH attempts fail, make fails loudly - correct, because
#     there is no safe degraded state to continue from.
#   * add UV_TOOL_DIR/UV_TOOL_BIN_DIR back. uv's default location is shared by every repo,
#     which is now correct: with no project dependencies in it, the env is identical for
#     all of them and there is nothing left to collide.
#
# BMK_MIN is kept as a floor even though nothing can cap bmk any more (that needed the
# co-resolution this recipe no longer does). It is inert insurance and costs nothing.
BMK_MIN := 3.9.0

# Refresh bmk's cached index metadata so a new release is seen the moment it exists -
# EXCEPT when uv is in offline mode, where uv refuses the combination outright ("the
# argument UV_OFFLINE cannot be used with --refresh") and would fail every single make
# with an error blaming an env var the user never connected to this flag. Offline then
# keeps working from the cache, which is exactly what an offline user wants anyway.
BMK_REFRESH := $(if $(UV_OFFLINE),,--refresh-package bmk)

.PHONY: _ensure_bmk
_ensure_bmk:
	@uv tool install --reinstall --force $(BMK_REFRESH) "bmk>=$(BMK_MIN)" \
	  || uv tool install --reinstall --force $(BMK_REFRESH) "bmk>=$(BMK_MIN)"

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

# The "$(ARGS)" quoting on commit/push is LOAD-BEARING - do not "tidy" it back to a bare
# $(ARGS) to match the other targets. These two take a MESSAGE and nothing else (both
# CLIs declare it as nargs=-1 with no options), so passing it as one quoted word costs
# nothing: bmk does
# " ".join(args).strip(), which round-trips a single arg unchanged, and empty ARGS still
# yields "" and falls through to BMK_COMMIT_MESSAGE / the prompt. What it buys is that
# bash stops parsing the message as code, so "fix(cli): x", "a; b" and *globs* survive.
# Flag-taking targets (test, run, custom, ...) must stay UNQUOTED - quoting them would
# collapse "--human -k foo" into a single argv element and break them.
.PHONY: commit c
commit: _ensure_bmk  ## Create a git commit with timestamped message [alias: c]
	$(BMK) commit "$(ARGS)"
c: _ensure_bmk
	$(BMK) commit "$(ARGS)"

.PHONY: push psh p
push: _ensure_bmk  ## Run tests, commit, and push to remote [aliases: psh, p]
	$(BMK) push "$(ARGS)"
psh p: _ensure_bmk
	$(BMK) push "$(ARGS)"

.PHONY: release rel r
release: _ensure_bmk  ## Create a versioned release (tag + GitHub release) [aliases: rel, r]
	$(BMK) release $(ARGS)
rel r: _ensure_bmk
	$(BMK) release $(ARGS)

# ship stays UNQUOTED although it does take a commit message, because unlike commit/push it
# also takes options (--ci-workflow, --release-workflow); one quoted word would swallow them.
# So give ship its message via MSG="..." (the env channel) and keep ARGS for its flags.
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
