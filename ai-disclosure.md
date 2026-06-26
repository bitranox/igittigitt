# AI disclosure

The author and owner of this project is the human, [@bitranox](https://github.com/bitranox).
Every design and engineering decision is theirs, and they answer for everything published here.
An AI assistant (Claude, run through the Claude Code CLI) was used as a tool along the way,
mostly for the typing and the legwork under that direction. This page says where, plainly, so
you can weigh the work on its merits. The reasoning behind working this way is in
[ai-stance.md](ai-stance.md).

## The human's work

The shape of this software is the human's, start to finish. They set the problem, made every
call, and own the result.

- The problem is theirs: `igittigitt` is a published gitignore parser (PyPI, up to v2.1.5) whose
  older releases openly documented that negations and nested-directory precedence were not handled
  correctly. The human's call was to rebuild it so the matching is exactly what git does, and to
  modernise the packaging at the same time.
- Every design decision was the human's. Rebuild from the bitranox CLI app template (for a dual
  library-plus-CLI shape), not the library template. A pure-Python, git-faithful matching engine
  validated by a differential test against the real `git check-ignore`, rather than wrapping the
  `git` binary at runtime (which would lose the pure-Python nature, be slower, and need a repo
  context). Keep the public API (`import igittigitt; igittigitt.IgnoreParser`) unchanged. Add a
  directory-aware include/whitelist mode. Keep memory bounded for very large trees. Drop `attrs`
  for `dataclasses` and `pydantic`. Restore the template's layered config and structured logging
  but remove the email subsystem. Expose the performance knobs through the layered config. Keep
  the published repo's history additive (no force-push, tags preserved). Ship a `python-gitignore`
  Claude Code skill, both as the repo's own plugin/marketplace and mirrored into the central
  bitranox-skills marketplace. Where there were options, the human picked.
- The human reviewed and corrected the work at each step and chose between the options the AI laid
  out (the engine approach, the include-mode semantics, how deep to restore the config/logging
  infrastructure, the tuning defaults). What ships is what they signed off on.
- Every commit goes out under the human's name and authority, with no AI co-author line. The human
  is responsible for what is published.

## Where the AI was used

As a tool, under the human's direction, it did the mechanical parts:

- Re-implemented the git evaluation algorithm to the human's brief: a single ordered pass with
  last-matching-pattern-wins, ancestor-directory pruning (a file under an excluded directory cannot
  be re-included), and per-directory precedence. It found, by checking against real git, that the
  faithful model needs no per-rule "contents" variation and relies on the ancestor walk instead.
- Built the differential test harness that compares igittigitt against `git check-ignore` over
  hand-written scenarios and randomised fuzz cases, and used it as the correctness oracle for every
  engine change.
- Implemented the two performance optimisations to the human's "make it fast but keep memory
  bounded" brief: compiling each glob to a cached regular expression, and memoizing the
  ancestor-directory decision in a bounded LRU. It measured the result (about 5x faster matching on
  tree-shaped workloads) and added tests that the caches stay within their caps.
- Carried out the template surgery: removing the email subsystem, restoring the layered-config and
  logging adapters, wiring the dependency-injected CLI, and exposing the `[performance]` knobs with
  measured defaults.
- Wrote the `python-gitignore` skill and its plugin/marketplace manifests, mirrored a copy into the
  bitranox-skills marketplace, and ran each documented example against the built package to confirm
  it works.

None of the decisions, and none of the accountability, were the AI's. The human directed and
approved every action and owns the result.

## What's been checked, and what hasn't

Checked locally (Linux, CPython 3.14): `ruff` and `ruff format`, `pyright` in strict mode (zero
errors), `import-linter` (three contracts: the core engine is independent of the adapters, the
domain is pure, and the clean-architecture layers hold), the full test suite (134 tests, about 84%
coverage), the differential suite agreeing with the installed `git` on every scenario and fuzz
case, the memory-boundedness tests, the include-mode `copytree` tests, real-subprocess pipe and
SIGPIPE tests, a wheel build, and the CLI end to end (`info`, `check`, `filter`, `config`,
`config-deploy`, `logdemo`). The skill's documented commands were each run against the install.

Not yet: the cross-platform CI matrix (Windows and macOS, and the full CPython 3.10 to 3.14 range)
that the project targets but that was not exercised on this machine; and no new PyPI release has
been cut. git compatibility is validated against the `git` version used in the tests; behaviour
that depends on a specific git build is only as correct as that comparison.

## Checking it yourself

You do not have to take any of this on faith.

- The source is available, and the matching engine is a single module.
- The differential tests live in the repository: `make test` (or `pytest tests/test_git_compat.py`)
  runs igittigitt against your own `git` and fails on any disagreement.
- The history is available too; decisions and reversals show up over time.

If something does not line up, open an issue.

## What this isn't

It is not a guarantee that every corner of git's wildmatch is reproduced beyond what the
differential tests cover, and it is not a reason to stop reading your own `.gitignore` rules. It is
a faithful, tested re-implementation, kept honest by comparing against the real thing.

## License and attribution

The text and code here are under the MIT License (see [`LICENSE`](LICENSE)). Anthropic's terms put
ownership of model output with the user, so the human owns this and answers for it.
