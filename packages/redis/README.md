# archipy-redis

Redis adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): caching, pub/sub and RediSearch.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[redis]"
```

## Usage

```python
from archipy.adapters.redis.adapters import RedisAdapter

adapter = RedisAdapter()
```

The adapter reads its settings from the `REDIS` section of the global config, for example `REDIS__<FIELD>` environment variables.

Classes in `archipy.adapters.redis.adapters`: `RedisAdapter`, `AsyncRedisAdapter`.

See the [Redis tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/redis/) for the full API.
