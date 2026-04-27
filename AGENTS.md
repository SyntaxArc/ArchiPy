# ArchiPy Agent Instructions

## Quick Commands

```bash
make format   # Ruff formatter (fixes in place)
make lint    # Ruff linter + ty type checker
make behave  # Run all BDD tests
make check   # format + lint + security + tests
make ci      # Full CI pipeline locally
```

## Essential Facts

- **Python 3.14+ required** — not 3.x
- Package manager: **UV** (never `pip install` directly)
- Tests: **Behave** BDD framework (not pytest)
- Run single test file: `uv run --extra behave behave features/redis_adapter.feature`

## Architecture

```
archipy/
├── models/      # Domain layer — entities, DTOs, errors
├── adapters/    # Infrastructure — external integrations
├── helpers/    # Utilities, decorators, interceptors
└── configs/    # pydantic-settings config
```

Import direction (one-way): `configs ← models ← helpers ← adapters`

## Key Conventions

- **Double quotes only** — Ruff enforces this
- **Google-style docstrings** on public functions
- Max line length: 120 characters
- McCabe complexity: max 10 per function

## Testing

- BDD steps use native `async def` (no `asyncio.run()` wrapper)
- Parallel execution: 8 workers (multiprocessing)
- Steps must not share mutable global state

## Dev Setup

```bash
make install-dev   # Install all deps + pre-commit hooks
make pre-commit  # Run hooks manually
```

## Linting Exclusions

`features/` and `scripts/` are excluded from Ruff linting.
