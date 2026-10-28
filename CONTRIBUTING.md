# Contributing Guide

Thanks for helping improve **igittigitt**. The sections below summarise the day-to-day workflow, highlight the repository automation, and list the checks that must pass before a change is merged.

## 1. Workflow Overview

1. Fork and branch -- use short, imperative branch names (`feature/cli-extension`, `fix/codecov-token`).
2. Make focused commits -- keep unrelated refactors out of the same change.
3. Run `make test` locally before pushing (see the automation note below).
4. Update documentation and changelog entries that are affected by the change.
5. Open a pull request referencing any relevant issues.

## 2. Commits & Pushes

- Commit messages should be imperative (`Add rich handler`, `Fix CLI exit codes`).
- The test harness (`make test`) runs the full lint/type/test pipeline. It creates no commit, but it may raise dependency floors in `pyproject.toml` and apply ruff's formatting and fixes, so review the working tree afterwards.
- `make push` runs the tests, commits and pushes. Give the message with `MSG="..."` (passed to bmk as `BMK_COMMIT_MESSAGE`); without one it prompts. `make help` lists every target.

## 3. Coding Standards

- Apply the repository's Clean Architecture / SOLID rules (see `CLAUDE.md` and the system prompts listed there).
- Prefer small, single-purpose modules and functions; avoid mixing orthogonal concerns.
- Free functions and modules use `snake_case`; classes are `PascalCase`.
- Keep runtime dependencies minimal. Use the standard library where practical.

## 4. Tests & Tooling

- `make test` runs Ruff (format + lint), bandit, import-linter, pip-audit, Pyright, and Pytest with coverage (all tests except those marked `integration`; CI runs all except `local_only`). See [DEVELOPMENT.md](DEVELOPMENT.md).
- `make dev` installs the package with its dev extras (`uv pip install -e ".[dev]"`).
- `make codecov` uploads the coverage report. For private repositories set `CODECOV_TOKEN` in your environment or `.env`.
- Tests follow a narrative style: prefer names like `test_when_<condition>_<outcome>()`, keep each case laser-focused, and mark OS constraints with the provided markers (`@pytest.mark.os_agnostic`, `@pytest.mark.os_windows`, etc.).
- Whenever you add a CLI behaviour or change metadata, update the relevant story in the `tests/test_cli*.py` files or `tests/test_metadata.py` so the specification remains complete.

## 5. Documentation Checklist

Before opening a PR, confirm the following:

- [ ] `make test` passes locally.
- [ ] Relevant documentation (`README.md`, `DEVELOPMENT.md`, `docs/systemdesign/*`) is updated.
- [ ] No generated artefacts or virtual environments are committed.
- [ ] Version bumps, when required, are made with `make bump-patch` / `bump-minor` / `bump-major`, which update `pyproject.toml`, `CHANGELOG.md` and `src/igittigitt/__init__conf__.py` together.

## 6. Security & Configuration

- Never commit secrets. Tokens (Codecov, PyPI) belong in `.env` (ignored by git) or CI secrets.
- Sanitise any payloads you emit via logging once richer logging features ship.

Happy hacking!
