# ArchiPy Agent Instructions

## Quick Commands

```bash
make format        # Ruff + gherkin-formatter (fixes in place)
make lint          # Ruff linter + ty type checker
make behave        # Run all BDD tests
make check         # format + lint + security + tests
make ci            # Full CI pipeline locally
make install-dev   # Install all deps + pre-commit hooks
make pre-commit    # Run hooks manually
```

Single feature:

```bash
uv run --extra behave behave features/redis_adapter.feature
uv run --extra behave behave features/redis_adapter.feature:42
```

Behave in CI (feature groups in `tests.yml`): `make behave FEATURE="features/a.feature" EXCLUDE="features/b.feature"`.

## Repo Map

- `archipy/` — core package: `models/`, `configs/`, `helpers/`, `adapters/`
- `packages/` — one workspace package per adapter (`redis`, `kafka`, `postgres`, ...), installed through extras
- `features/` — Behave `.feature` files, `steps/`, `test_containers.py`
- `scripts/` — tooling (`behave_parallel.py`); `docs/` — MkDocs site and changelog

## Essential Facts

- **Python 3.14+** required
- Package manager: **`uv`** (never `pip install` directly)
- Tests: **Behave** BDD (not pytest)
- CI install: `uv sync --locked --all-extras`
- Import direction: `models ← configs ← helpers ← adapters` (enforced by `make lint` via import-linter)

## Rule Index

Canonical policies live in `.cursor/rules/`. Start with `rules-index.mdc` for ownership and precedence.

| Need                       | Rule                                                       |
|----------------------------|------------------------------------------------------------|
| Layers / imports           | `architecture-patterns.mdc`                                |
| Adapters                   | `adapter-conventions.mdc`                                  |
| Models / errors            | `models-errors.mdc`                                        |
| Helpers / configs          | `helpers-configs.mdc`                                      |
| Style                      | `python-code-style.mdc`                                    |
| Typing                     | `typing-strict.mdc`                                        |
| BDD                        | `testing-bdd.mdc`                                          |
| Security                   | `security.mdc`                                             |
| Commits / PRs              | `contributing.mdc`                                         |
| Tooling                    | `tooling-workflow.mdc`                                     |
| Docs / changelog / release | `documentation.mdc`, `changelog.mdc`, `github-release.mdc` |

## Don't

- No `pip install`, no pytest, no mocks when a testcontainer exists
- No breaking changes: keep the old path and emit `DeprecationWarning`
- No `sleep` loops or long timeouts in tests
- No mention of AI tools in commits, issues or PRs
- No new feature file without a matching group in `.github/workflows/tests.yml` (otherwise it runs in `core`); see `testing-bdd.mdc`

## Definition of Done

`make format` and `make lint` clean, BDD scenario added or updated, `make security` when touching adapters/auth/crypto/network. Changelog only per `changelog.mdc`.

## Rules Loading

`.cursor/rules/*.mdc` carry `globs`/`alwaysApply` frontmatter. Tools that ignore it: read `rules-index.mdc` first, then the rule that owns the path you edit.

## Git Conventions

Conventional commits (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`). Branches `feat|fix|chore|ci/<topic>`; never `docs/...` (a branch named `docs` exists, use `chore/<topic>`).

## Findings Workflow

Bugs/issues/improvements found: create GitHub issue first, fix, open PR (`Closes #N`), merge. One PR = one small chunk: split big work into several issues, or several PRs with `Part of #N` (only the last `Closes #N`). After each merged PR, update its issue (checklist, results). Label every issue and PR (type, area, priority; see `contributing.mdc`). Changelog-only PRs need no issue. Details: `contributing.mdc`.

## Gotchas

`features/` and `scripts/` are excluded from Ruff linting; still follow the style rules by hand.
