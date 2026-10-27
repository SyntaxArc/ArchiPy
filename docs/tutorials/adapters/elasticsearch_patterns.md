---
title: Elasticsearch Patterns
description: Repository pattern and advanced patterns for the ArchiPy Elasticsearch adapter.
---

# Elasticsearch Patterns

Patterns built on top of the ArchiPy Elasticsearch adapter. Start with the
[Elasticsearch Adapter Tutorial](elasticsearch.md) for configuration, indexing, search, bulk and async basics.

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
        except InternalError as e:
            logger.error(f"Failed to save article {article_id}: {e}")
            raise

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
        except InternalError as e:
            logger.error(f"Failed to retrieve article {article_id}: {e}")
            raise

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
        except InternalError as e:
            logger.error(f"Failed to search articles by author={author}: {e}")
            raise

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
        except InternalError as e:
            logger.error(f"Failed to increment views for article {article_id}: {e}")
            raise

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

from elasticsearch import ApiError, Elasticsearch

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
except ApiError as e:
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
    except InternalError as e:
        logger.error(f"Elasticsearch health check failed: {e}")
        raise ServiceUnavailableError() from e

    if not es.ping():
        raise ServiceUnavailableError()
    logger.info("Elasticsearch cluster is healthy")
    return es
```

### Observability (OpenTelemetry)

The Elasticsearch **adapter** (`ElasticsearchAdapter` / `AsyncElasticsearchAdapter`) is unchanged
in 5.0.0. Elastic APM (`ElasticsearchAPMConfig` / `ELASTIC_APM`) was removed — use OpenTelemetry
instead.

The `elasticsearch` client emits OTel spans natively — no extra instrumentor needed. Install `archipy[otel]` and enable
OTel:

```bash
uv add "archipy[otel]"
```

```bash
OTEL__IS_ENABLED=true
OTEL__OTLP_ENDPOINT=http://localhost:4317
OTEL__TRACES_ENABLED=true
OTEL__METRICS_ENABLED=true
```

`OtelUtils.init_otel_if_needed` (via `AppUtils.create_fastapi_app` / `create_grpc_app`, or
manually) instruments the Elasticsearch client library when that extra is installed. See
[Observability](../observability.md) for full configuration.

## See Also

- [Elasticsearch Adapter Tutorial](elasticsearch.md) — Configuration, CRUD, search, bulk and async usage
- [Observability](../observability.md) — OpenTelemetry (replaces Elastic APM)
- [API Reference](../../api_reference/adapters/elasticsearch.md) — Full Elasticsearch adapter API documentation
