# ArchiPy Agent Instructions

## Quick Commands

```bash
make format        # Ruff formatter (fixes in place)
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

## Essential Facts

- **Python 3.14+** required
- Package manager: **`uv`** (never `pip install` directly)
- Tests: **Behave** BDD (not pytest)
- Import direction: `configs ← models ← helpers ← adapters`

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
| Code exploration           | `graphify.mdc`                                             |

## Linting Exclusions

`features/` and `scripts/` are excluded from Ruff linting.
