# archipy-mysql

MySQL adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): SQLAlchemy access to MySQL.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[mysql]"
uv add "archipy[mysql-async]"
```

## Usage

```python
from archipy.adapters.mysql.sqlalchemy.adapters import MySQLSQLAlchemyAdapter

adapter = MySQLSQLAlchemyAdapter()
```

The adapter reads its settings from the `MYSQL_SQLALCHEMY` section of the global config, for example `MYSQL_SQLALCHEMY__<FIELD>` environment variables.

Classes in `archipy.adapters.mysql.sqlalchemy.adapters`: `MySQLSQLAlchemyAdapter`, `AsyncMySQLSQLAlchemyAdapter`.

See the [MySQL tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/mysql/) for the full API.
