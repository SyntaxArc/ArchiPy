# archipy-sqlite

SQLite adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): SQLAlchemy access to SQLite.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[aiosqlite]"
```

## Usage

```python
from archipy.adapters.sqlite.sqlalchemy.adapters import SQLiteSQLAlchemyAdapter

adapter = SQLiteSQLAlchemyAdapter()
```

The adapter reads its settings from the `SQLITE_SQLALCHEMY` section of the global config, for example `SQLITE_SQLALCHEMY__<FIELD>` environment variables.

Classes in `archipy.adapters.sqlite.sqlalchemy.adapters`: `SQLiteSQLAlchemyAdapter`, `AsyncSQLiteSQLAlchemyAdapter`.

See the [SQLite tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/sqlite/) for the full API.
