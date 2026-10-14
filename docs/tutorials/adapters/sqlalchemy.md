---
title: SQLAlchemy Search Totals
description: How the PostgreSQL, MySQL, SQLite and StarRocks adapters count the total of a paginated search, and how to keep that count cheap on large tables.
---

# SQLAlchemy Search Totals

`execute_search_query` is shared by the [PostgreSQL](postgres.md), [MySQL](mysql.md), [SQLite](sqlite.md) and
[StarRocks](starrocks.md) adapters, sync and async. It returns the page of entities and the total number of matching
rows.

## How the total is counted

- The total is read from the page when that is enough: no pagination, or a first page that is not full. No `COUNT`
  runs.
- Otherwise a `COUNT` runs over the primary key of the entity, without the ordering, so the database can answer from the
  primary key index. A query that uses `DISTINCT`, `GROUP BY`, `HAVING`, `LIMIT`, `OFFSET` or `FETCH` keeps its own
  columns, because they change the row count.

## Count threshold

`count_threshold=N` keeps the total exact up to `N` rows. Above that, PostgreSQL returns the planner estimate instead of
scanning every row. MySQL, SQLite and StarRocks still count exactly. The estimate depends on table statistics, so keep
autovacuum and `ANALYZE` healthy.

```python
users, total = adapter.execute_search_query(
    entity=User,
    query=base_query,
    pagination=pagination,
    count_threshold=10_000,
)
```

`COUNT_THRESHOLD` in the SQLAlchemy config sets the same threshold for every search that passes none. It is unset by
default, which means the total is always exact.

## Count cache

With `COUNT_CACHE_ENABLED=true` each total is cached in process, so only the first page of a search runs a `COUNT` and
later pages reuse the total. A total can be stale for up to the TTL, so a row created just before a search may be
missing from it.

| Setting                   | Default | Meaning                                    |
|---------------------------|---------|--------------------------------------------|
| `COUNT_CACHE_ENABLED`     | `false` | Turns the cache on                         |
| `COUNT_CACHE_TTL_SECONDS` | `60`    | Seconds a cached total stays valid         |
| `COUNT_CACHE_MAX_SIZE`    | `1000`  | Number of cached searches kept per adapter |

The cache is off by default and needs the `cache` extra: `ttl_cache` serves the sync adapter and `async-lru` serves the
async one. Enabling it without the extra fails when the adapter is created.

## See Also

- [PostgreSQL Adapter](postgres.md), [MySQL Adapter](mysql.md), [SQLite Adapter](sqlite.md) and
  [StarRocks Adapter](starrocks.md) — Adapter tutorials
- [Configuration Management](../config_management.md) — Setting the `SQLALCHEMY` config values
- [API Reference](../../api_reference/adapters/postgres.md) — Full adapter API documentation
