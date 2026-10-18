# archipy-elasticsearch

Elasticsearch adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): search and indexing.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[elasticsearch]"
uv add "archipy[elasticsearch-async]"
```

## Usage

```python
from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter

adapter = ElasticsearchAdapter()
```

The adapter reads its settings from the `ELASTIC` section of the global config, for example `ELASTIC__<FIELD>` environment variables.

Classes in `archipy.adapters.elasticsearch.adapters`: `ElasticsearchAdapter`, `AsyncElasticsearchAdapter`.

See the [Elasticsearch tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/elasticsearch/) for the full API.
