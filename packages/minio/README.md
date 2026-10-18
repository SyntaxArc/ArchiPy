# archipy-minio

MinIO adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): S3-compatible object storage.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[minio]"
```

## Usage

```python
from archipy.adapters.minio.adapters import MinioAdapter

adapter = MinioAdapter()
```

The adapter reads its settings from the `MINIO` section of the global config, for example `MINIO__<FIELD>` environment variables.

Classes in `archipy.adapters.minio.adapters`: `MinioAdapter`.

See the [MinIO tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/minio/) for the full API.
