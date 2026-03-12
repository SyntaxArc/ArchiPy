---
title: Elasticsearch Adapter Guide
description: Practical examples for using the ArchiPy Elasticsearch adapter.
---

# Elasticsearch Adapter Guide

This guide demonstrates how to use the ArchiPy Elasticsearch adapter for document indexing, searching, and cluster
management with proper error handling and Python 3.14+ type hints.

## Installation

```bash
uv add "archipy[elasticsearch]"
```

!!! tip
The Elasticsearch adapter is an optional extra. Only install it when you need Elasticsearch support to keep your
environment lean.

## Configuration

Configure Elasticsearch via environment variables or an `ElasticsearchConfig` object directly.

### Environment Variables

```bash
# Basic connection
ELASTIC__HOSTS='["https://localhost:9200"]'

# Basic auth (alternative to API key)
ELASTIC__HTTP_USER_NAME=elastic
ELASTIC__HTTP_PASSWORD=your-password

# API key auth (preferred over basic auth)
ELASTIC__API_KEY=your-api-key-id
ELASTIC__API_SECRET=your-api-key-secret

# TLS/SSL
ELASTIC__CA_CERTS=/path/to/ca.crt
ELASTIC__VERIFY_CERTS=true

# Connection behaviour
ELASTIC__REQUEST_TIMEOUT=5.0
ELASTIC__MAX_RETRIES=3
ELASTIC__RETRY_ON_TIMEOUT=true
```

### Direct Configuration

```python
import logging

from archipy.configs.config_template import ElasticsearchConfig
from archipy.models.errors import ConfigurationError

logger = logging.getLogger(__name__)

try:
    es_config = ElasticsearchConfig(
        HOSTS=["https://localhost:9200"],
        # API key auth (takes precedence over HTTP basic auth)
        API_KEY="my-key-id",
        API_SECRET="my-key-secret",  # type: ignore[arg-type]
        # TLS
        CA_CERTS="/path/to/ca.crt",
        VERIFY_CERTS=True,
        # Timeouts and retries
        REQUEST_TIMEOUT=5.0,
        MAX_RETRIES=3,
        RETRY_ON_TIMEOUT=True,
        RETRY_ON_STATUS=(429, 502, 503, 504),
        # Connection pool
        CONNECTIONS_PER_NODE=10,
        HTTP_COMPRESS=True,
    )
except Exception as e:
    logger.error(f"Invalid Elasticsearch configuration: {e}")
    raise ConfigurationError() from e
else:
    logger.info("Elasticsearch configuration created successfully")
```

## Basic Usage

### Synchronous Adapter

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

# Uses global config (BaseConfig.global_config().ELASTIC)
try:
    es = ElasticsearchAdapter()
except Exception as e:
    logger.error(f"Failed to create Elasticsearch adapter: {e}")
    raise InternalError() from e
else:
    logger.info("Elasticsearch adapter initialised")
```

To use a custom config instead of the global one:

```python
from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.configs.config_template import ElasticsearchConfig

custom_config = ElasticsearchConfig(HOSTS=["https://es.internal:9200"])
es = ElasticsearchAdapter(elasticsearch_config=custom_config)
```

### Asynchronous Adapter

```python
import asyncio
import logging

from archipy.adapters.elasticsearch.adapters import AsyncElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        es = AsyncElasticsearchAdapter()
        pong = await es.ping()
        logger.info(f"Cluster reachable: {pong}")
    except Exception as e:
        logger.error(f"Elasticsearch connection failed: {e}")
        raise InternalError() from e


asyncio.run(main())
```

## Index Management

### Create an Index

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

index_body = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "analysis": {
            "analyzer": {
                "custom_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop"],
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "title": {"type": "text", "analyzer": "custom_analyzer"},
            "content": {"type": "text"},
            "author": {"type": "keyword"},
            "published_at": {"type": "date"},
            "view_count": {"type": "integer"},
            "tags": {"type": "keyword"},
        }
    },
}

try:
    if not es.index_exists("articles"):
        response = es.create_index("articles", body=index_body)
        logger.info(f"Index created: {response}")
    else:
        logger.info("Index already exists, skipping creation")
except Exception as e:
    logger.error(f"Failed to create index: {e}")
    raise InternalError() from e
```

### Delete an Index

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

try:
    if es.index_exists("articles"):
        es.delete_index("articles")
        logger.info("Index deleted")
    else:
        logger.info("Index does not exist, nothing to delete")
except Exception as e:
    logger.error(f"Failed to delete index: {e}")
    raise InternalError() from e
```

## Document Operations

### Index a Document

```python
import logging
from datetime import datetime, timezone

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

article: dict[str, str | int | list[str]] = {
    "title": "Getting Started with ArchiPy",
    "content": "ArchiPy provides clean-architecture building blocks for Python services.",
    "author": "alice",
    "published_at": datetime.now(tz=timezone.utc).isoformat(),
    "view_count": 0,
    "tags": ["python", "architecture", "clean-code"],
}

try:
    # Index with an explicit document ID
    response = es.index(index="articles", document=article, doc_id="article-001")
    logger.info(f"Document indexed: {response['result']}")

    # Index without specifying an ID — Elasticsearch auto-generates one
    response = es.index(index="articles", document=article)
    generated_id: str = response["_id"]
    logger.info(f"Document auto-indexed with id={generated_id}")
except Exception as e:
    logger.error(f"Failed to index document: {e}")
    raise InternalError() from e
```

### Retrieve a Document

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError, NotFoundError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

try:
    response = es.get(index="articles", doc_id="article-001")
    document = response["_source"]
    logger.info(f"Retrieved document: title={document['title']}")
except KeyError as e:
    logger.warning(f"Document not found: {e}")
    raise NotFoundError() from e
except Exception as e:
    logger.error(f"Failed to retrieve document: {e}")
    raise InternalError() from e
```

### Check Document Existence

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

exists = es.exists(index="articles", doc_id="article-001")
logger.info(f"Document exists: {exists}")
```

### Update a Document

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

# Partial update — only the specified fields are changed
update_fields: dict[str, int] = {"view_count": 42}

try:
    response = es.update(index="articles", doc_id="article-001", doc=update_fields)
    logger.info(f"Document updated: {response['result']}")
except Exception as e:
    logger.error(f"Failed to update document: {e}")
    raise InternalError() from e
```

### Delete a Document

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

try:
    response = es.delete(index="articles", doc_id="article-001")
    logger.info(f"Document deleted: {response['result']}")
except Exception as e:
    logger.error(f"Failed to delete document: {e}")
    raise InternalError() from e
```

## Search

### Match Query

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

query: dict[str, object] = {
    "query": {
        "match": {
            "content": "clean architecture"
        }
    }
}

try:
    response = es.search(index="articles", query=query)
    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]
    logger.info(f"Found {total} documents")
    for hit in hits:
        logger.info(f"  [{hit['_score']:.2f}] {hit['_source']['title']}")
except Exception as e:
    logger.error(f"Search failed: {e}")
    raise InternalError() from e
```

### Bool Query with Filters

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

query: dict[str, object] = {
    "query": {
        "bool": {
            "must": [
                {"match": {"content": "python"}}
            ],
            "filter": [
                {"term": {"author": "alice"}},
                {"range": {"view_count": {"gte": 10}}},
            ],
        }
    },
    "sort": [{"published_at": {"order": "desc"}}],
    "size": 10,
    "from": 0,
}

try:
    response = es.search(index="articles", query=query)
    hits = response["hits"]["hits"]
    logger.info(f"Filtered results: {len(hits)} documents")
    for hit in hits:
        src = hit["_source"]
        logger.info(f"  {src['title']} by {src['author']} ({src['view_count']} views)")
except Exception as e:
    logger.error(f"Filtered search failed: {e}")
    raise InternalError() from e
```

### Full-Text Search with Highlighting

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

query: dict[str, object] = {
    "query": {
        "multi_match": {
            "query": "clean architecture python",
            "fields": ["title^2", "content"],  # title boosted 2x
        }
    },
    "highlight": {
        "fields": {
            "title": {},
            "content": {"fragment_size": 150, "number_of_fragments": 3},
        }
    },
}

try:
    response = es.search(index="articles", query=query)
    for hit in response["hits"]["hits"]:
        title = hit["_source"]["title"]
        highlights = hit.get("highlight", {}).get("content", [])
        logger.info(f"Title: {title}")
        for fragment in highlights:
            logger.info(f"  ...{fragment}...")
except Exception as e:
    logger.error(f"Highlighted search failed: {e}")
    raise InternalError() from e
```

### Aggregations

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

query: dict[str, object] = {
    "size": 0,  # No document hits — only aggregations
    "aggs": {
        "authors": {
            "terms": {"field": "author", "size": 10}
        },
        "tags": {
            "terms": {"field": "tags", "size": 20}
        },
        "avg_views": {
            "avg": {"field": "view_count"}
        },
    },
}

try:
    response = es.search(index="articles", query=query)
    aggs = response["aggregations"]

    logger.info("Top authors:")
    for bucket in aggs["authors"]["buckets"]:
        logger.info(f"  {bucket['key']}: {bucket['doc_count']} articles")

    logger.info("Top tags:")
    for bucket in aggs["tags"]["buckets"]:
        logger.info(f"  {bucket['key']}: {bucket['doc_count']} articles")

    logger.info(f"Average view count: {aggs['avg_views']['value']:.1f}")
except Exception as e:
    logger.error(f"Aggregation query failed: {e}")
    raise InternalError() from e
```

## Bulk Operations

Use `bulk()` to index, update, or delete many documents in a single API call, dramatically reducing network overhead.

### Bulk Indexing

```python
import logging
from datetime import datetime, timezone

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

articles = [
    {"id": f"article-{i:03d}", "title": f"Article {i}", "author": "bob", "view_count": i * 10}
    for i in range(1, 101)
]

# Build actions list in Elasticsearch bulk format
actions: list[dict[str, object]] = []
for article in articles:
    actions.append({"index": {"_index": "articles", "_id": article["id"]}})
    actions.append({
        "title": article["title"],
        "author": article["author"],
        "view_count": article["view_count"],
        "published_at": datetime.now(tz=timezone.utc).isoformat(),
        "tags": ["bulk", "import"],
    })

try:
    response = es.bulk(actions=actions)
    errors = response.get("errors", False)
    if errors:
        failed = [item for item in response["items"] if "error" in item.get("index", {})]
        logger.error(f"Bulk index completed with {len(failed)} errors")
    else:
        logger.info(f"Bulk index successful: {len(articles)} documents indexed")
except Exception as e:
    logger.error(f"Bulk index failed: {e}")
    raise InternalError() from e
```

### Bulk Update

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

es = ElasticsearchAdapter()

updates: list[tuple[str, int]] = [
    ("article-001", 150),
    ("article-002", 89),
    ("article-003", 210),
]

actions: list[dict[str, object]] = []
for doc_id, new_view_count in updates:
    actions.append({"update": {"_index": "articles", "_id": doc_id}})
    actions.append({"doc": {"view_count": new_view_count}})

try:
    response = es.bulk(actions=actions)
    logger.info(f"Bulk update complete, errors={response.get('errors', False)}")
except Exception as e:
    logger.error(f"Bulk update failed: {e}")
    raise InternalError() from e
```

## Async Usage

### Async Document Indexing and Search

```python
import asyncio
import logging
from datetime import datetime, timezone

from archipy.adapters.elasticsearch.adapters import AsyncElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)


async def index_and_search() -> None:
    es = AsyncElasticsearchAdapter()

    try:
        # Create index if absent
        if not await es.index_exists("articles"):
            await es.create_index("articles", body={
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "author": {"type": "keyword"},
                        "published_at": {"type": "date"},
                    }
                }
            })
            logger.info("Index created")

        # Index a document
        await es.index(
            index="articles",
            document={
                "title": "Async Elasticsearch with ArchiPy",
                "author": "carol",
                "published_at": datetime.now(tz=timezone.utc).isoformat(),
            },
            doc_id="async-001",
        )
        logger.info("Document indexed")

        # Search
        response = await es.search(
            index="articles",
            query={"query": {"match": {"author": "carol"}}},
        )
        total = response["hits"]["total"]["value"]
        logger.info(f"Found {total} documents by carol")
    except Exception as e:
        logger.error(f"Async Elasticsearch operation failed: {e}")
        raise InternalError() from e


asyncio.run(index_and_search())
```

### Concurrent Async Operations

```python
import asyncio
import logging
from datetime import datetime, timezone

from archipy.adapters.elasticsearch.adapters import AsyncElasticsearchAdapter
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)


async def parallel_searches() -> None:
    es = AsyncElasticsearchAdapter()

    queries = [
        {"query": {"match": {"author": "alice"}}},
        {"query": {"match": {"author": "bob"}}},
        {"query": {"range": {"view_count": {"gte": 100}}}},
    ]

    try:
        results = await asyncio.gather(
            *[es.search(index="articles", query=q) for q in queries],
            return_exceptions=True,
        )
    except Exception as e:
        logger.error(f"Parallel search failed: {e}")
        raise InternalError() from e

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Query {i} failed: {result}")
        else:
            total = result["hits"]["total"]["value"]
            logger.info(f"Query {i}: {total} documents")


asyncio.run(parallel_searches())
```

## Repository Pattern

Wrap the adapter behind a repository class to keep domain logic clean.

```python
import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.adapters.elasticsearch.ports import ElasticsearchPort
from archipy.models.errors import InternalError, NotFoundError

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Domain model for an article."""

    title: str
    content: str
    author: str
    tags: list[str]
    published_at: str = ""
    view_count: int = 0

    def __post_init__(self) -> None:
        if not self.published_at:
            self.published_at = datetime.now(tz=timezone.utc).isoformat()


class ArticleRepository:
    """Repository for Article documents backed by Elasticsearch.

    Args:
        es_adapter: Elasticsearch port implementation to use.
    """

    INDEX = "articles"

    def __init__(self, es_adapter: ElasticsearchPort) -> None:
        self._es = es_adapter

    def save(self, article_id: str, article: Article) -> None:
        """Persist an article to the index.

        Args:
            article_id: Unique identifier for the article.
            article: Article domain object to persist.

        Raises:
            InternalError: If the Elasticsearch operation fails.
        """
        try:
            self._es.index(index=self.INDEX, document=asdict(article), doc_id=article_id)
            logger.info(f"Saved article id={article_id}")
        except Exception as e:
            logger.error(f"Failed to save article {article_id}: {e}")
            raise InternalError() from e

    def get(self, article_id: str) -> Article:
        """Retrieve an article by ID.

        Args:
            article_id: Unique identifier of the article.

        Returns:
            The matching Article domain object.

        Raises:
            NotFoundError: If no article with the given ID exists.
            InternalError: If the Elasticsearch operation fails.
        """
        try:
            response = self._es.get(index=self.INDEX, doc_id=article_id)
            src = response["_source"]
            return Article(**src)
        except KeyError as e:
            raise NotFoundError() from e
        except Exception as e:
            logger.error(f"Failed to retrieve article {article_id}: {e}")
            raise InternalError() from e

    def search_by_author(self, author: str) -> Sequence[Article]:
        """Search articles by author.

        Args:
            author: Author name to filter by.

        Returns:
            Sequence of matching Article objects.

        Raises:
            InternalError: If the search fails.
        """
        try:
            response = self._es.search(
                index=self.INDEX,
                query={"query": {"term": {"author": author}}},
            )
            return [Article(**hit["_source"]) for hit in response["hits"]["hits"]]
        except Exception as e:
            logger.error(f"Failed to search articles by author={author}: {e}")
            raise InternalError() from e

    def increment_views(self, article_id: str) -> None:
        """Increment the view count for an article.

        Args:
            article_id: Unique identifier of the article.

        Raises:
            InternalError: If the update fails.
        """
        try:
            self._es.update(
                index=self.INDEX,
                doc_id=article_id,
                doc={"view_count": self._get_view_count(article_id) + 1},
            )
        except Exception as e:
            logger.error(f"Failed to increment views for article {article_id}: {e}")
            raise InternalError() from e

    def _get_view_count(self, article_id: str) -> int:
        response = self._es.get(index=self.INDEX, doc_id=article_id)
        return int(response["_source"].get("view_count", 0))


# Usage
repo = ArticleRepository(ElasticsearchAdapter())

article = Article(
    title="Clean Architecture in Python",
    content="How to structure Python services for long-term maintainability.",
    author="alice",
    tags=["python", "architecture"],
)

repo.save("arch-001", article)
found = repo.get("arch-001")
logger.info(f"Retrieved: {found.title}")

repo.increment_views("arch-001")
alice_articles = repo.search_by_author("alice")
logger.info(f"Alice has {len(alice_articles)} articles")
```

## Advanced Patterns

### Index Alias Strategy

Use aliases so you can swap underlying indices without changing application code (useful for zero-downtime
re-indexing).

```python
import logging

from elasticsearch import Elasticsearch

from archipy.configs.config_template import ElasticsearchConfig

logger = logging.getLogger(__name__)

config = ElasticsearchConfig(HOSTS=["https://localhost:9200"])
client = Elasticsearch(
    hosts=config.HOSTS,
    basic_auth=(config.HTTP_USER_NAME, config.HTTP_PASSWORD.get_secret_value())
    if config.HTTP_USER_NAME and config.HTTP_PASSWORD
    else None,
)

# Create a versioned index and point the alias at it
try:
    client.indices.create(index="articles_v1", body={
        "mappings": {"properties": {"title": {"type": "text"}}}
    })
    client.indices.put_alias(index="articles_v1", name="articles")
    logger.info("Created articles_v1 with alias articles")
except Exception as e:
    logger.error(f"Alias setup failed: {e}")
    raise
```

### Connection Health Check

```python
import logging

from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.models.errors import ServiceUnavailableError

logger = logging.getLogger(__name__)


def ensure_elasticsearch_ready() -> ElasticsearchAdapter:
    """Create an adapter and verify the cluster is reachable.

    Returns:
        A connected ElasticsearchAdapter.

    Raises:
        ServiceUnavailableError: If the cluster does not respond to a ping.
    """
    try:
        es = ElasticsearchAdapter()
        if not es.ping():
            raise ServiceUnavailableError()
        logger.info("Elasticsearch cluster is healthy")
        return es
    except Exception as e:
        logger.error(f"Elasticsearch health check failed: {e}")
        raise ServiceUnavailableError() from e
```

### APM Integration

Use `ElasticsearchAPMConfig` to enable Elastic APM for distributed tracing in your service:

```python
import elasticapm  # type: ignore[import-untyped]

from archipy.configs.base_config import BaseConfig


class AppConfig(BaseConfig):
    APP_NAME: str = "my-service"


config = AppConfig()
apm_cfg = config.ELASTIC_APM

if apm_cfg.IS_ENABLED:
    apm_client = elasticapm.Client(
        server_url=apm_cfg.SERVER_URL,
        service_name=apm_cfg.SERVICE_NAME,
        secret_token=apm_cfg.SECRET_TOKEN.get_secret_value() if apm_cfg.SECRET_TOKEN else None,
        environment=apm_cfg.ENVIRONMENT,
        transaction_sample_rate=apm_cfg.TRANSACTION_SAMPLE_RATE,
    )
    elasticapm.instrument()
```

## Troubleshooting

### `ConnectionError` on startup

- Verify `ELASTIC__HOSTS` includes the correct scheme (`https://` or `http://`).
- Ensure the Elasticsearch cluster is running: `curl -u elastic:<password> https://localhost:9200`.
- When `VERIFY_CERTS=True`, confirm `CA_CERTS` points to a valid CA bundle.

### `AuthenticationException` (401)

- API key auth takes precedence over HTTP basic auth. If both are set, only the API key is used.
- Rotate the API key if it has been revoked or expired.

### `BulkIndexError` during `bulk()`

- The adapter raises `BulkIndexError` on partial failures. Inspect `error.errors` for per-document details.
- Common causes: mapping conflict (a field value does not match its declared type), shard unavailability.

### High latency under load

- Increase `CONNECTIONS_PER_NODE` for concurrent workloads.
- Enable `HTTP_COMPRESS=True` to reduce payload sizes.
- Use `bulk()` instead of individual `index()` calls for batch writes.
- Set a realistic `REQUEST_TIMEOUT` to surface slow queries early.

### Sniffing warnings

- `ElasticsearchConfig` logs a warning when sniffing is enabled with a single non-localhost host — this may bypass
  load balancers. Disable sniffing (`SNIFF_ON_START=False`, `SNIFF_BEFORE_REQUESTS=False`) when connecting through
  a load balancer or Elastic Cloud.

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — Elasticsearch configuration setup
- [API Reference](../../api_reference/adapters/elasticsearch.md) — Full Elasticsearch adapter API documentation
- [Elasticsearch Python Client docs](https://www.elastic.co/guide/en/elasticsearch/client/python-api/current/index.html)
