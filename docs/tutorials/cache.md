---
title: Caching
description: In-process TTL caching with the ttl_cache decorator and the cache extra.
---

# Caching

The `cache` extra installs `cachetools` and `async-lru`. ArchiPy exposes one public helper on top of it:
`ttl_cache`, an in-process TTL and LRU decorator backed by `cachetools.TTLCache`. `async-lru` is used internally by the
async SQLAlchemy count cache (see [SQLAlchemy Search Totals](adapters/sqlalchemy.md)); ArchiPy has no public wrapper
for it. For a shared cache across processes, use the [Redis adapter](adapters/redis.md).

## Installation

```bash
uv add "archipy[cache]"
```

Without the extra, applying `ttl_cache` raises `ConfigurationError` with a hint to install `archipy[cache]`.

## Basic Usage

```python
import logging

from archipy.helpers.decorators import ttl_cache

logger = logging.getLogger(__name__)


@ttl_cache(ttl_seconds=60, maxsize=100)
def get_exchange_rate(currency: str) -> float:
    """Return a rate; the result is cached for 60 seconds."""
    logger.info("Fetching rate for %s", currency)
    return 1.0


get_exchange_rate("EUR")  # runs the function
get_exchange_rate("EUR")  # served from the cache
get_exchange_rate.clear_cache()
```

| Argument      | Default | Meaning                                                                       |
|---------------|---------|-------------------------------------------------------------------------------|
| `ttl_seconds` | `300`   | Seconds an entry lives; or a zero-argument callable returning it (see below)  |
| `maxsize`     | `100`   | Entry limit; the least recently used entry is evicted when full               |

## Async Functions

`async def` functions work with the same decorator. The awaited value is cached:

```python
import logging

from archipy.helpers.decorators import ttl_cache

logger = logging.getLogger(__name__)


@ttl_cache(ttl_seconds=30)
async def load_profile(user_id: str) -> dict[str, str]:
    """Load a profile; the awaited result is cached for 30 seconds."""
    logger.info("Loading profile %s", user_id)
    return {"id": user_id}
```

## Methods

On instance methods the cache is **shared by all instances** and the instance is part of the call, not of the key
(see Behavior). Use it for work that depends only on the arguments:

```python
import logging

from archipy.helpers.decorators import ttl_cache

logger = logging.getLogger(__name__)


class PriceService:
    """Looks up prices."""

    @ttl_cache(ttl_seconds=60, maxsize=50)
    def price_of(self, sku: str) -> float:
        """Return the price of a SKU."""
        logger.info("Computing price for %s", sku)
        return 9.99


first = PriceService()
second = PriceService()
first.price_of("A1")
second.price_of("A1")  # served from the cache
first.price_of.clear_cache()
```

## Config-Driven TTL

`ttl_seconds` accepts a callable. It is evaluated once, when the decorator is applied:

```python
from archipy.helpers.decorators import ttl_cache


def lookup_ttl() -> int:
    """Return the TTL; read it from your own config section."""
    return 120


@ttl_cache(ttl_seconds=lookup_ttl)
def expensive_lookup(key: str) -> str:
    """Cache with a TTL resolved once at import time."""
    return key.upper()
```

## Behavior

- Exceptions are not cached; the next call runs the function again.
- `None` results are cached like any other value.
- Argument types are part of the key: `f(1)` and `f(1.0)` are separate entries.
- Unhashable arguments (for example a `list`) bypass the cache and run the function.
- Cache access is guarded by a lock, so threads can share one decorated function.
- On methods, `self` is passed to the function but is not part of the key, so two instances share entries.
- The cache lives in the process. It is not shared between workers and is lost on restart.

## Deprecated Names

`ttl_cache_decorator` is a deprecated alias that emits a `DeprecationWarning`; the module path
`archipy.helpers.decorators.cache` is a kept legacy import path. Use `ttl_cache` from `archipy.helpers.decorators`.

## Tests

The behavior above is covered by the `features/cache_decorator.feature` scenarios (basic caching, TTL expiry, maxsize,
instance methods, `clear_cache`).

## See Also

- [Decorators](helpers/decorators.md) - Other decorators
- [Redis Adapter](adapters/redis.md) - Cache shared across processes
- [SQLAlchemy Search Totals](adapters/sqlalchemy.md) - The count cache built on the `cache` extra
- [Installation](../getting-started/installation.md) - All extras
