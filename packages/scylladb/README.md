# archipy-scylladb

ScyllaDB adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): Cassandra-compatible CQL access.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[scylladb]"
```

## Usage

```python
from archipy.adapters.scylladb.adapters import ScyllaDBAdapter

adapter = ScyllaDBAdapter()
```

The adapter reads its settings from the `SCYLLADB` section of the global config, for example `SCYLLADB__<FIELD>` environment variables.

Classes in `archipy.adapters.scylladb.adapters`: `ScyllaDBAdapter`, `AsyncScyllaDBAdapter`.

See the [ScyllaDB tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/scylladb/) for the full API.
