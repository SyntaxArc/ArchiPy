# archipy-temporal

Temporal adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): workflow orchestration.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[temporalio]"
```

## Usage

```python
from archipy.adapters.temporal.adapters import TemporalAdapter

adapter = TemporalAdapter()
```

The adapter reads its settings from the `TEMPORAL` section of the global config, for example `TEMPORAL__<FIELD>` environment variables.

Classes in `archipy.adapters.temporal.adapters`: `TemporalAdapter`.

See the [Temporal tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/temporal/) for the full API.
