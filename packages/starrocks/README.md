# archipy-starrocks

StarRocks adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): SQLAlchemy access to StarRocks.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[starrocks]"
uv add "archipy[starrocks-async]"
```

## Usage

```python
from archipy.adapters.starrocks.sqlalchemy.adapters import StarrocksSQLAlchemyAdapter

adapter = StarrocksSQLAlchemyAdapter()
```

The adapter reads its settings from the `STARROCKS_SQLALCHEMY` section of the global config, for example `STARROCKS_SQLALCHEMY__<FIELD>` environment variables.

Classes in `archipy.adapters.starrocks.sqlalchemy.adapters`: `StarrocksSQLAlchemyAdapter`, `AsyncStarrocksSQLAlchemyAdapter`.

See the [StarRocks tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/starrocks/) for the full API.
