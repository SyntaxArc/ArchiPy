---
title: Redis Adapter Tutorial
description: Practical examples for using the ArchiPy Redis adapter, including caching, pub/sub, and RediSearch.
---

# Redis Adapter Tutorial

This guide demonstrates how to use the ArchiPy Redis adapter for common caching,
key-value storage, and RediSearch (full-text, vector KNN, and hybrid search).

## Installation

First, ensure you have the Redis dependencies installed:

```bash
uv add "archipy[redis]"
```

> **Tip:** The Redis adapter is an optional extra. Install only when Redis support is needed.

## Configuration

Configure Redis via environment variables or a `RedisConfig` object.

### Environment Variables

```bash
REDIS__MASTER_HOST=localhost
REDIS__PORT=6379
REDIS__PASSWORD=your-password
REDIS__DATABASE=0
REDIS__MAX_CONNECTIONS=50
```

### Direct Configuration

```python
from archipy.configs.config_template import RedisConfig

config = RedisConfig(
    MASTER_HOST="localhost",
    PORT=6379,
    PASSWORD=None,
    DATABASE=0,
)
```

## Basic Usage

### Synchronous Redis Adapter

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Uses global config (BaseConfig.global_config().REDIS)
    redis = RedisAdapter()

    # Set and get values
    redis.set("user:123:name", "John Doe")
    name = redis.get("user:123:name")
    logger.info(f"User name: {name}")

    # Set with expiration (ex = seconds)
    redis.set("session:456", "active", ex=3600)

    # Delete a key
    redis.delete("user:123:name")

    # Check if key exists
    if redis.exists("session:456"):
        logger.info("Session exists")
except CacheError as e:
    logger.error(f"Redis operation failed: {e}")
    raise
```

To use a custom config instead of the global one:

```python
from archipy.adapters.redis.adapters import RedisAdapter
from archipy.configs.config_template import RedisConfig

custom_config = RedisConfig(MASTER_HOST="redis.internal", PORT=6379)
redis = RedisAdapter(redis_config=custom_config)
```

### Asynchronous Redis Adapter

```python
import asyncio
import logging

from archipy.adapters.redis.adapters import AsyncRedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        redis = AsyncRedisAdapter()

        # Async operations
        await redis.set("counter", "1")
        await redis.incrby("counter")  # Increment by 1
        count = await redis.get("counter")
        logger.info(f"Counter: {count}")
    except CacheError as e:
        logger.error(f"Redis operation failed: {e}")
        raise


asyncio.run(main())
```

## Caching Patterns

### Function Result Caching

```python
import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

redis = RedisAdapter()


def cache_result(key_prefix: str, ttl: int = 300) -> Callable[[T], T]:
    """Decorator to cache function results in Redis.

    Args:
        key_prefix: Prefix for the Redis cache key.
        ttl: Time-to-live in seconds (default: 5 minutes).

    Returns:
        Decorated function with Redis caching.
    """

    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            try:
                cached = redis.get(cache_key)
                if cached:
                    return json.loads(cached)

                result = func(*args, **kwargs)
                redis.set(cache_key, json.dumps(result), ex=ttl)
                return result
            except CacheError as e:
                logger.warning(f"Redis error, falling back to direct call: {e}")
                return func(*args, **kwargs)

        return cast(T, wrapper)

    return decorator


@cache_result("api", ttl=60)
def expensive_api_call(item_id: int) -> dict[str, str | int]:
    """Simulate an expensive API call.

    Args:
        item_id: ID of the item to fetch.

    Returns:
        Item data dictionary.
    """
    logger.info("Executing expensive operation...")
    time.sleep(1)
    return {"id": item_id, "name": f"Item {item_id}", "data": "Some data"}


# First call executes the function
result1 = expensive_api_call(123)
logger.info(f"First call: {result1}")

# Second call returns the cached result
result2 = expensive_api_call(123)
logger.info(f"Second call (cached): {result2}")
```

## Advanced Redis Features

### Publish/Subscribe

The `publish` and `pubsub` methods are available through the port interface:

```python
import logging
import threading
import time

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)


def subscribe_thread() -> None:
    try:
        subscriber = RedisAdapter()
        pubsub = subscriber.pubsub()

        def message_handler(message: dict[str, str]) -> None:
            if message["type"] == "message":
                logger.info(f"Received message: {message['data']}")

        pubsub.subscribe(**{"channel:notifications": message_handler})
        pubsub.run_in_thread(sleep_time=0.5)
        time.sleep(10)
        pubsub.close()
    except CacheError as e:
        logger.error(f"Redis subscription error: {e}")
        raise


try:
    thread = threading.Thread(target=subscribe_thread)
    thread.start()
    time.sleep(1)

    redis = RedisAdapter()
    for i in range(5):
        redis.publish("channel:notifications", f"Notification {i}")
        time.sleep(1)

    thread.join()
except CacheError as e:
    logger.error(f"Redis publisher error: {e}")
    raise
```

### Pipeline for Multiple Operations

Use `get_pipeline()` to batch commands and reduce round-trips:

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)

try:
    redis = RedisAdapter()

    # Batch set operations
    pipe = redis.get_pipeline()
    pipe.set("stats:visits", 0)
    pipe.set("stats:unique_users", 0)
    pipe.set("stats:conversion_rate", "0.0")
    pipe.execute()

    # Batch increment operations
    pipe = redis.get_pipeline()
    pipe.incrby("stats:visits")
    pipe.incrby("stats:unique_users")
    results: list[int] = pipe.execute()
    logger.info(f"Visits: {results[0]}, Unique users: {results[1]}")
except CacheError as e:
    logger.error(f"Redis pipeline error: {e}")
    raise
```

### Increment a Counter

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)

redis = RedisAdapter()

try:
    redis.set("page_views", "0")
    redis.incrby("page_views")           # increment by 1
    redis.incrby("page_views", amount=5) # increment by 5
    count = redis.get("page_views")
    logger.info(f"Page views: {count}")
except CacheError as e:
    logger.error(f"Counter error: {e}")
    raise
```

### INCREX Window Counter

Redis 8.8 adds the `INCREX` command — a generalized increment with optional bounds and conditional expiration.
ArchiPy exposes it as `increx()` on both sync and async adapters. It is the primitive behind
[FastAPI rate limiting](../helpers/interceptors.md#rate-limiting-dependency).

> **Note:** Redis **8.8+** is required. The test container image in `.env.test` is `redis:8.8.0-alpine`.
> `fakeredis` does not implement `INCREX`; use a real Redis 8.8 instance to exercise this command.

`increx` returns a two-element list: `[new_value, actual_increment_applied]`. When `actual_increment_applied` is
`0`, the increment was rejected or clamped at the bound.

#### Synchronous example

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

logger = logging.getLogger(__name__)

redis = RedisAdapter()

try:
    new_value, applied = redis.increx(
        "rate:api:user-1",
        byint=1,
        ubound=5,
        saturate=True,
        px=60_000,
        enx=True,
    )
    logger.info(f"Counter: {new_value}, applied: {applied}")
except CacheError as e:
    logger.error(f"INCREX failed: {e}")
    raise
```

#### Asynchronous example

```python
import asyncio
import logging

from archipy.adapters.redis.adapters import AsyncRedisAdapter
from archipy.models.errors import CacheError

logger = logging.getLogger(__name__)


async def main() -> None:
    redis = AsyncRedisAdapter()
    try:
        new_value, applied = await redis.increx(
            "rate:api:user-1",
            byint=1,
            ubound=5,
            saturate=True,
            px=60_000,
            enx=True,
        )
        logger.info(f"Counter: {new_value}, applied: {applied}")
    except CacheError as e:
        logger.error(f"INCREX failed: {e}")
        raise


asyncio.run(main())
```

#### Parameters

| Parameter | Description |
|---|---|
| `byint` / `byfloat` | Increment step (mutually exclusive; defaults to 1) |
| `lbound` / `ubound` | Lower and upper bounds on the resulting value |
| `saturate` | Clamp to the bound instead of rejecting when out of range |
| `ex` / `px` | Relative expiry in seconds or milliseconds |
| `exat` / `pxat` | Absolute expiry timestamp |
| `persist` | Remove any existing expiration |
| `enx` | Set expiration only when the key has no TTL (preserves window start) |

## RediSearch

ArchiPy exposes RediSearch through index-bound handles returned by `search_index()`. Each handle covers index
management, document upserts, full-text search, vector KNN, hybrid search, aggregations, and aliases.

> **Note:** RediSearch requires **Redis Stack** (or a Redis build with the RediSearch and RedisJSON modules). The
> adapter uses a dedicated binary-safe client (`decode_responses=False`) for vector fields. RediSearch only works in
> **standalone** mode — cluster and sentinel configurations raise `ConfigurationError`.

### Create an Index

Define the schema with DTO field configs, then create a HASH or JSON index with a key prefix:

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.dtos.redis.search.index_schema_dto import (
    IndexSchemaDTO,
    TagFieldConfig,
    TextFieldConfig,
    VectorFieldConfig,
)
from archipy.models.types.redis_search_types import (
    RedisIndexType,
    VectorAlgorithm,
    VectorDistanceMetric,
)

logger = logging.getLogger(__name__)

redis = RedisAdapter()
handle = redis.search_index("products")

schema = IndexSchemaDTO(
    fields=[
        TextFieldConfig(name="title"),
        TagFieldConfig(name="category"),
        VectorFieldConfig(
            name="embedding",
            dim=3,
            distance_metric=VectorDistanceMetric.COSINE,
            algorithm=VectorAlgorithm.HNSW,
        ),
    ],
    index_type=RedisIndexType.HASH,
)

handle.create_index(schema, prefix="product:")
logger.info("RediSearch index created")
```

For JSON documents, set `index_type=RedisIndexType.JSON`. Field names are mapped to JSON paths (`$.title`, etc.)
automatically.

### Upsert Documents

HASH documents store scalar fields in a Redis hash and pack vectors as float32 bytes:

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.dtos.redis.search.document_dto import HashDocumentUpsertDTO

logger = logging.getLogger(__name__)

redis = RedisAdapter()
handle = redis.search_index("products")

handle.upsert_hash(
    "product:1",
    {"title": "Redis Guide", "category": "books"},
    vector_field="embedding",
    vector=[1.0, 0.0, 0.0],
)

handle.upsert_hash_dto(
    HashDocumentUpsertDTO(
        doc_id="product:2",
        fields={"title": "Python Guide", "category": "books"},
        vector_field="embedding",
        vector=[0.0, 1.0, 0.0],
    ),
)
logger.info("HASH documents indexed")
```

JSON documents store the full payload at a JSON path (default `$`):

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.dtos.redis.search.document_dto import JsonDocumentUpsertDTO

logger = logging.getLogger(__name__)

redis = RedisAdapter()
handle = redis.search_index("products-json")

handle.upsert_json(
    "json:1",
    {"title": "JSON Book", "category": "books", "embedding": [0.0, 0.0, 1.0]},
)

handle.upsert_json_dto(
    JsonDocumentUpsertDTO(
        doc_id="json:2",
        payload={"title": "Another Book", "embedding": [0.5, 0.5, 0.0]},
    ),
)
logger.info("JSON documents indexed")
```

Use `pack_vector()` and `unpack_vector()` from `archipy.adapters.redis.search` when you need to convert embeddings
outside the adapter:

```python
from archipy.adapters.redis.search import pack_vector, unpack_vector

blob = pack_vector([1.0, 0.0, 0.0])
vector = unpack_vector(blob, dim=3)
```

### Vector KNN Search

Build a KNN query with `SearchQueryDTO.from_knn()`:

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.dtos.redis.search.search_query_dto import SearchQueryDTO

logger = logging.getLogger(__name__)

redis = RedisAdapter()
handle = redis.search_index("products")

result = handle.search(
    SearchQueryDTO.from_knn(
        [0.9, 0.1, 0.0],
        k=1,
        return_fields=["title"],
    ),
)

top_hit = result.hits[0]
logger.info(f"Top hit: {top_hit.doc_id} — {top_hit.fields.get('title')} (score={top_hit.score})")
```

### Full-Text and Hybrid Search

Full-text search uses a `SearchQueryDTO` with a text query string. Hybrid search combines full-text and vector KNN:

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.dtos.redis.search.search_query_dto import SearchQueryDTO

logger = logging.getLogger(__name__)

redis = RedisAdapter()
handle = redis.search_index("products")

text_result = handle.search(
    SearchQueryDTO(query="@title:database", return_fields=["title"], limit=5),
)

hybrid_result = handle.search(
    SearchQueryDTO.from_hybrid(
        "database",
        [0.8, 0.2, 0.0],
        k=3,
        return_fields=["title"],
    ),
)

logger.info(f"Text hits: {text_result.total}, hybrid hits: {len(hybrid_result.hits)}")
```

### Aggregations

Group and count documents with `AggregationDTO`:

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.dtos.redis.search.aggregation_dto import AggregationDTO

logger = logging.getLogger(__name__)

redis = RedisAdapter()
handle = redis.search_index("products")

agg = handle.aggregate(
    AggregationDTO(
        query="*",
        group_by=["category"],
        reduce_function="COUNT",
        reduce_field="count",
    ),
)

logger.info(f"Aggregation rows: {agg['rows']}")
```

### Schema Changes, Aliases, and Index Lifecycle

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.dtos.redis.search.index_schema_dto import NumericFieldConfig

logger = logging.getLogger(__name__)

redis = RedisAdapter()
handle = redis.search_index("products")

handle.alter_schema_add(NumericFieldConfig(name="price"))
handle.add_alias("products-view")
handle.update_alias("products-view")

indexes = redis.list_search_indexes()
logger.info(f"Indexes: {indexes}")

handle.drop_index(delete_documents=True)
handle.delete_alias("products-view")
```

### Asynchronous RediSearch

The async adapter exposes the same handle API with `await`:

```python
import asyncio
import logging

from archipy.adapters.redis.adapters import AsyncRedisAdapter
from archipy.models.dtos.redis.search.search_query_dto import SearchQueryDTO

logger = logging.getLogger(__name__)


async def main() -> None:
    redis = AsyncRedisAdapter()
    handle = redis.search_index("products")

    await handle.upsert_hash(
        "product:1",
        {"title": "Async Redis"},
        vector_field="embedding",
        vector=[1.0, 0.0, 0.0],
    )

    result = await handle.search(
        SearchQueryDTO.from_knn([0.9, 0.1, 0.0], k=1, return_fields=["title"]),
    )
    logger.info(f"Async search hits: {result.total}")


asyncio.run(main())
```

### Document Retrieval and Deletion

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter

logger = logging.getLogger(__name__)

redis = RedisAdapter()
handle = redis.search_index("products")

document = handle.get_document("product:1")
logger.info(f"Document title: {document.get('title')}")

handle.delete_document("product:1", delete_actual_document=True)
```

## Error Handling

The Redis adapter maps connection and command failures to `CacheError`:

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

logger = logging.getLogger(__name__)

try:
    redis = RedisAdapter()
    redis.set("session:1", "active", ex=3600)
    value = redis.get("session:1")
except CacheError as e:
    logger.error(f"Redis operation failed: {e}")
    raise
else:
    logger.info(f"Session value: {value}")
```

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — Redis configuration setup
- [BDD Testing](../testing_strategy.md) — Testing Redis operations
- [Cache Decorator](../helpers/decorators.md#cache-decorator) — TTL cache decorator usage
- [Interceptors - Rate Limiting](../helpers/interceptors.md#rate-limiting-dependency) — FastAPI rate limiting with `INCREX`
- [BDD Testing](../testing_strategy.md) — RediSearch scenarios in `features/redis_adapter.feature`
- [API Reference](../../api_reference/adapters/redis.md) — Full Redis adapter API documentation
