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

`COUNT_THRESHOLD` in the SQLAlchemy config sets the same threshold for every search that passes none. When it is unset,
`BaseConfig.set_global()` fills it with `PAGINATION.MAX_ITEMS` (default `10000`), the deepest `page * page_size` a
`PaginationDTO` accepts, because past that row no page can be requested and an exact total is of no use. Set
`COUNT_THRESHOLD` to a larger number to count exactly for longer.

## Telling an estimate from an exact total

`execute_search_query` returns only the number, and the estimate is always above the threshold. A search output that
extends `SearchOutputDTO` reports that as `total_count_estimated`, so an API can show "10000+" instead of an invented
number:

```python
from archipy.models.dtos.search_output_dto import ExactSearchOutputDTO, SearchOutputDTO


class SearchUsersOutputDTO(SearchOutputDTO):
    items: list[UserDTO]


class ListRolesOutputDTO(ExactSearchOutputDTO):
    items: list[RoleDTO]
```

`SearchOutputDTO` reads `COUNT_THRESHOLD` from `POSTGRES_SQLALCHEMY` (set `count_threshold_config` in a subclass for
another config) and is meaningful on PostgreSQL only, because the other databases count exactly.
`ExactSearchOutputDTO` has the same fields with `total_count_estimated` always `false`, for searches that count on their
own. A total that was counted exactly but is above the threshold, for example a first page larger than the threshold, is
reported as estimated too.

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
