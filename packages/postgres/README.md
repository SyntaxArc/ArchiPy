# archipy-postgres

PostgreSQL adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): SQLAlchemy access to PostgreSQL.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[postgres]"
```

## Usage

```python
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter

adapter = PostgresSQLAlchemyAdapter()
```

The adapter reads its settings from the `POSTGRES_SQLALCHEMY` section of the global config, for example `POSTGRES_SQLALCHEMY__<FIELD>` environment variables.

Classes in `archipy.adapters.postgres.sqlalchemy.adapters`: `PostgresSQLAlchemyAdapter`, `AsyncPostgresSQLAlchemyAdapter`.

See the [PostgreSQL tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/postgres/) for the full API.
