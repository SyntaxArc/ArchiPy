---
title: PostgreSQL Adapter Tutorial
description: Practical examples for using the ArchiPy PostgreSQL adapter.
---

# PostgreSQL Adapter Tutorial

This guide demonstrates how to use the ArchiPy PostgreSQL adapter for database operations with SQLAlchemy, covering
configuration, CRUD, transactions, filtering, pagination, async patterns, and testing.

## Installation

```bash
uv add "archipy[postgres]"
```

> **Tip:** The PostgreSQL adapter is an optional extra. Install it alongside any ORM extras you need, for example
`archipy[postgres]`.

## Configuration

Configure the adapter via environment variables or a `PostgresSQLAlchemyConfig` object.

### Environment Variables

```bash
# Individual fields
POSTGRES_SQLALCHEMY__HOST=localhost
POSTGRES_SQLALCHEMY__PORT=5432
POSTGRES_SQLALCHEMY__DATABASE=mydb
POSTGRES_SQLALCHEMY__USERNAME=myuser
POSTGRES_SQLALCHEMY__PASSWORD=secret

# Or provide a full DSN (the adapter will parse the components automatically)
POSTGRES_SQLALCHEMY__POSTGRES_DSN=postgresql+psycopg://myuser:secret@localhost:5432/mydb

# Connection pool
POSTGRES_SQLALCHEMY__POOL_SIZE=20
POSTGRES_SQLALCHEMY__POOL_MAX_OVERFLOW=5
POSTGRES_SQLALCHEMY__POOL_TIMEOUT=30
POSTGRES_SQLALCHEMY__POOL_RECYCLE_SECONDS=600

# SQL logging (useful for debugging)
POSTGRES_SQLALCHEMY__ECHO=false
```

### Direct Configuration

```python
import logging

from archipy.configs.config_template import PostgresSQLAlchemyConfig
from archipy.models.errors import ConfigurationError

logger = logging.getLogger(__name__)

try:
    pg_config = PostgresSQLAlchemyConfig(
        HOST="localhost",
        PORT=5432,
        DATABASE="mydb",
        USERNAME="myuser",
        PASSWORD="secret",
        # Pool settings
        POOL_SIZE=20,
        POOL_MAX_OVERFLOW=5,
        POOL_TIMEOUT=30,
        POOL_RECYCLE_SECONDS=600,
        POOL_USE_LIFO=True,
        POOL_PRE_PING=True,
        # Isolation level
        ISOLATION_LEVEL="REPEATABLE READ",
    )
except Exception as e:
    logger.error(f"Invalid PostgreSQL configuration: {e}")
    raise ConfigurationError() from e
else:
    logger.info("PostgreSQL configuration created successfully")
```

DSN-style configuration also works — the adapter automatically parses and back-fills the individual fields:

```python
from archipy.configs.config_template import PostgresSQLAlchemyConfig

# DSN is parsed and individual fields (HOST, PORT, DATABASE, etc.) are populated
pg_config = PostgresSQLAlchemyConfig(
    POSTGRES_DSN="postgresql+psycopg://myuser:secret@localhost:5432/mydb"
)
```

## Defining Entities

```python
from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from archipy.models.entities.sqlalchemy.base_entities import (
    BaseEntity,
    DeletableEntity,
    UpdatableEntity,
)


class User(UpdatableEntity):
    """User entity with automatic update-timestamp tracking."""

    __tablename__ = "users"

    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)

    posts: list["Post"] = relationship("Post", back_populates="author")


class Post(DeletableEntity):
    """Post entity with soft-delete support."""

    __tablename__ = "posts"

    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(ForeignKey("users.uuid"), nullable=False)

    author: User = relationship("User", back_populates="posts")
```

## Basic Usage

### Synchronous Adapter

```python
import logging

from archipy.adapters.base.sqlalchemy.adapters import (
    SQLAlchemyFilterMixin,
    SQLAlchemyPaginationMixin,
    SQLAlchemySortMixin,
)
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.errors import DatabaseConnectionError, DatabaseQueryError

logger = logging.getLogger(__name__)


class UserPostgresAdapter(PostgresSQLAlchemyAdapter, SQLAlchemyFilterMixin, SQLAlchemyPaginationMixin,
                          SQLAlchemySortMixin):
    """PostgreSQL adapter with filter, pagination, and sort query capabilities for the User domain."""


# Uses global config (BaseConfig.global_config().POSTGRES_SQLALCHEMY)
try:
    adapter = UserPostgresAdapter()
except (DatabaseConnectionError, DatabaseQueryError) as e:
    logger.error(f"Failed to create PostgreSQL adapter: {e}")
    raise
else:
    logger.info("PostgreSQL adapter initialised")
```

To use a custom config instead of the global one:

```python
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.configs.config_template import PostgresSQLAlchemyConfig

custom_config = PostgresSQLAlchemyConfig(HOST="pg.internal", PORT=5432, DATABASE="mydb")
adapter = PostgresSQLAlchemyAdapter(orm_config=custom_config)
```

### Create Tables

```python
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity

adapter = PostgresSQLAlchemyAdapter()

# Create all tables registered in the metadata
BaseEntity.metadata.create_all(adapter.session_manager.engine)
```

## CRUD Operations

All operations must run inside an active SQLAlchemy session, usually provided by the `@postgres_sqlalchemy_atomic`
decorator (see [Transactions](#transactions) below).

### Create

```python
import logging

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.errors import AlreadyExistsError, DatabaseQueryError

logger = logging.getLogger(__name__)

adapter = PostgresSQLAlchemyAdapter()


def create_user(username: str, email: str, full_name: str) -> User:
    """Create a new user.

    Args:
        username: Unique username.
        email: Unique email address.
        full_name: Display name.

    Returns:
        The created User entity (with UUID and timestamps populated).

    Raises:
        AlreadyExistsError: If a user with the same username or email exists.
        DatabaseQueryError: If the database operation fails.
    """
    try:
        user = User(username=username, email=email, full_name=full_name)
        result = adapter.create(user)
    except AlreadyExistsError:
        logger.warning(f"User already exists: {username}")
        raise
    except DatabaseQueryError as e:
        logger.error(f"Failed to create user {username}: {e}")
        raise
    else:
        logger.info(f"Created user uuid={result.uuid}")
        return result
```

### Bulk Create

```python
import logging

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.errors import DatabaseQueryError

logger = logging.getLogger(__name__)

adapter = PostgresSQLAlchemyAdapter()


def bulk_import_users(user_data: list[dict[str, str]]) -> list[User]:
    """Import multiple users in a single flush.

    Args:
        user_data: List of dicts with ``username`` and ``email`` keys.

    Returns:
        The created User entities.

    Raises:
        DatabaseQueryError: If the bulk operation fails.
    """
    users = [User(username=d["username"], email=d["email"]) for d in user_data]
    try:
        result = adapter.bulk_create(users)
    except DatabaseQueryError as e:
        logger.error(f"Bulk create failed: {e}")
        raise

    logger.info(f"Bulk created {len(result)} users")
    return result
```

### Read by UUID

```python
import logging
from uuid import UUID

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.errors import DatabaseQueryError, NotFoundError

logger = logging.getLogger(__name__)

adapter = PostgresSQLAlchemyAdapter()


def get_user(user_id: UUID) -> User:
    """Retrieve a user by UUID.

    Args:
        user_id: The user's UUID.

    Returns:
        The User entity.

    Raises:
        NotFoundError: If no user with the given UUID exists.
        DatabaseQueryError: If the database operation fails.
    """
    try:
        user = adapter.get_by_uuid(User, user_id)
    except DatabaseQueryError as e:
        logger.error(f"Failed to fetch user {user_id}: {e}")
        raise

    if user is None:
        raise NotFoundError()
    return user
```

### Update

```python
import logging
from uuid import UUID

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.errors import DatabaseQueryError, NotFoundError

logger = logging.getLogger(__name__)

adapter = PostgresSQLAlchemyAdapter()


def update_user_email(user_id: UUID, new_email: str) -> User:
    """Update a user's email address.

    Args:
        user_id: UUID of the user to update.
        new_email: New email address.

    Returns:
        The updated User entity.

    Raises:
        NotFoundError: If the user does not exist.
        DatabaseQueryError: If the database operation fails.
    """
    try:
        user = adapter.get_by_uuid(User, user_id)
    except DatabaseQueryError as e:
        logger.error(f"Failed to fetch user for update: {e}")
        raise

    if user is None:
        raise NotFoundError()

    try:
        user.email = new_email
        session = adapter.get_session()
        session.flush()
    except DatabaseQueryError as e:
        logger.error(f"Failed to update user {user_id}: {e}")
        raise

    logger.info(f"Updated email for user uuid={user_id}")
    return user
```

### Delete

```python
import logging
from uuid import UUID

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.errors import DatabaseQueryError, NotFoundError

logger = logging.getLogger(__name__)

adapter = PostgresSQLAlchemyAdapter()


def delete_user(user_id: UUID) -> None:
    """Delete a user by UUID.

    Args:
        user_id: UUID of the user to delete.

    Raises:
        NotFoundError: If the user does not exist.
        DatabaseQueryError: If the database operation fails.
    """
    try:
        user = adapter.get_by_uuid(User, user_id)
    except DatabaseQueryError as e:
        logger.error(f"Failed to fetch user for deletion: {e}")
        raise

    if user is None:
        raise NotFoundError()

    try:
        adapter.delete(user)
    except DatabaseQueryError as e:
        logger.error(f"Failed to delete user {user_id}: {e}")
        raise

    logger.info(f"Deleted user uuid={user_id}")
```

## Transactions

Use the `@postgres_sqlalchemy_atomic_decorator` to wrap operations in a transaction. If any exception is raised, the
entire transaction is automatically rolled back.

```python
import logging

from archipy.helpers.decorators.sqlalchemy_atomic import postgres_sqlalchemy_atomic_decorator
from archipy.models.errors import AlreadyExistsError, DatabaseQueryError

logger = logging.getLogger(__name__)

adapter = PostgresSQLAlchemyAdapter()


@postgres_sqlalchemy_atomic_decorator
def create_user_with_post(username: str, email: str, post_title: str, post_content: str) -> tuple[User, Post]:
    """Create a user and their first post atomically.

    If any part fails, the entire transaction is rolled back automatically.

    Args:
        username: User's username.
        email: User's email address.
        post_title: Title of the initial post.
        post_content: Content of the initial post.

    Returns:
        Tuple of (User, Post) created together.

    Raises:
        AlreadyExistsError: If a user with the same username or email exists.
        DatabaseQueryError: If a database error occurs.
    """
    try:
        user = adapter.create(User(username=username, email=email))
        post = adapter.create(Post(title=post_title, content=post_content, author_id=user.uuid))
    except AlreadyExistsError:
        logger.warning(f"User {username} already exists")
        raise
    except DatabaseQueryError as e:
        logger.error(f"Transaction failed: {e}")
        raise

    logger.info(f"Created user={user.uuid} and post={post.uuid}")
    return user, post
```

## Searching, Filtering, and Pagination

Use `execute_search_query` with `PaginationDTO` and `SortDTO` for rich queries, building filter conditions directly with
SQLAlchemy's `.where()`.

```python
import logging
from uuid import UUID

from sqlalchemy import select

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.dtos.pagination_dto import PaginationDTO
from archipy.models.dtos.sort_dto import SortDTO
from archipy.models.errors import DatabaseQueryError
from archipy.models.types.base_types import SortOrderType

logger = logging.getLogger(__name__)

adapter = PostgresSQLAlchemyAdapter()


def search_users(
        search_term: str | None = None,
        page: int = 1,
        page_size: int = 20,
) -> tuple[list[User], int]:
    """Search users with optional full-name filter, pagination, and sorting.

    Args:
        search_term: Optional string to match against ``full_name``.
        page: 1-based page number.
        page_size: Number of results per page.

    Returns:
        Tuple of (list of User entities, total count).

    Raises:
        DatabaseQueryError: If the query fails.
    """
    base_query = select(User)

    if search_term:
        base_query = base_query.where(User.full_name.ilike(f"%{search_term}%"))

    pagination = PaginationDTO(page=page, page_size=page_size)
    sort_info = SortDTO(field=User.username, order=SortOrderType.ASCENDING)

    try:
        users, total = adapter.execute_search_query(
            entity=User,
            query=base_query,
            pagination=pagination,
            sort_info=sort_info,
        )
    except DatabaseQueryError as e:
        logger.error(f"User search failed: {e}")
        raise

    logger.info(f"Found {total} users (page {page})")
    return users, total
```

### Available Filter Operations

| Operation               | Behaviour                                   |
|-------------------------|---------------------------------------------|
| `EQUAL`                 | `field = value`                             |
| `NOT_EQUAL`             | `field != value`                            |
| `LESS_THAN`             | `field < value`                             |
| `LESS_THAN_OR_EQUAL`    | `field <= value`                            |
| `GREATER_THAN`          | `field > value`                             |
| `GREATER_THAN_OR_EQUAL` | `field >= value`                            |
| `IN_LIST`               | `field IN (...)` — value must be a list     |
| `NOT_IN_LIST`           | `field NOT IN (...)` — value must be a list |
| `LIKE`                  | `field LIKE %value%` (case-sensitive)       |
| `ILIKE`                 | `field ILIKE %value%` (case-insensitive)    |
| `STARTS_WITH`           | `field LIKE value%`                         |
| `ENDS_WITH`             | `field LIKE %value`                         |
| `CONTAINS`              | Alias for `ILIKE` — `field ILIKE %value%`   |
| `IS_NULL`               | `field IS NULL`                             |
| `IS_NOT_NULL`           | `field IS NOT NULL`                         |

## Raw SQL Execution

For queries that fall outside the ORM, use `execute()` or `scalars()` directly:

```python
import logging

from sqlalchemy import text

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.models.errors import DatabaseQueryError

logger = logging.getLogger(__name__)

adapter = PostgresSQLAlchemyAdapter()


def count_active_users() -> int:
    """Count users created in the last 30 days.

    Returns:
        Number of recently created users.

    Raises:
        DatabaseQueryError: If the query fails.
    """
    sql = text("SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '30 days'")
    try:
        result = adapter.execute(sql)
        count = result.scalar_one()
    except DatabaseQueryError as e:
        logger.error(f"Count query failed: {e}")
        raise

    logger.info(f"Active users in last 30 days: {count}")
    return int(count)
```

## Async Usage

> **Tip:** Async PostgreSQL support requires the `sqlalchemy-async` extra:

```bash
uv add "archipy[postgres,sqlalchemy-async]"
```

### Asynchronous Adapter

```python
import asyncio
import logging

from archipy.adapters.postgres.sqlalchemy.adapters import AsyncPostgresSQLAlchemyAdapter
from archipy.models.errors import DatabaseConnectionError, DatabaseQueryError

logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        adapter = AsyncPostgresSQLAlchemyAdapter()
    except (DatabaseConnectionError, DatabaseQueryError) as e:
        logger.error(f"Failed to create async adapter: {e}")
        raise
    else:
        logger.info("Async PostgreSQL adapter initialised")


asyncio.run(main())
```

### Async CRUD

```python
import asyncio
import logging
from uuid import UUID

from archipy.adapters.postgres.sqlalchemy.adapters import AsyncPostgresSQLAlchemyAdapter
from archipy.models.errors import DatabaseQueryError, NotFoundError

logger = logging.getLogger(__name__)

adapter = AsyncPostgresSQLAlchemyAdapter()


async def async_create_user(username: str, email: str) -> User:
    """Create a user asynchronously.

    Args:
        username: Unique username.
        email: Unique email address.

    Returns:
        The created User entity.

    Raises:
        DatabaseQueryError: If the database operation fails.
    """
    try:
        user = await adapter.create(User(username=username, email=email))
    except DatabaseQueryError as e:
        logger.error(f"Async create failed: {e}")
        raise
    else:
        logger.info(f"Async created user uuid={user.uuid}")
        return user


async def async_get_user(user_id: UUID) -> User:
    """Retrieve a user asynchronously by UUID.

    Args:
        user_id: The user's UUID.

    Returns:
        The matching User entity.

    Raises:
        NotFoundError: If no user with the given UUID exists.
        DatabaseQueryError: If the database operation fails.
    """
    try:
        user = await adapter.get_by_uuid(User, user_id)
    except DatabaseQueryError as e:
        logger.error(f"Async get failed: {e}")
        raise

    if user is None:
        raise NotFoundError()
    return user


asyncio.run(async_create_user("async_alice", "async@example.com"))
```

### Async Transactions

```python
import asyncio
import logging

from archipy.helpers.decorators.sqlalchemy_atomic import async_postgres_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError

logger = logging.getLogger(__name__)

adapter = AsyncPostgresSQLAlchemyAdapter()


@async_postgres_sqlalchemy_atomic_decorator
async def async_create_user_with_post(username: str, email: str, title: str) -> tuple[User, Post]:
    """Create a user and a post asynchronously in a single transaction.

    Args:
        username: User's username.
        email: User's email address.
        title: Title of the initial post.

    Returns:
        Tuple of (User, Post).

    Raises:
        DatabaseQueryError: If the database operation fails.
    """
    try:
        user = await adapter.create(User(username=username, email=email))
        post = await adapter.create(Post(title=title, content="...", author_id=user.uuid))
    except DatabaseQueryError as e:
        logger.error(f"Async transaction failed: {e}")
        raise

    logger.info(f"Async created user={user.uuid} post={post.uuid}")
    return user, post


asyncio.run(async_create_user_with_post("bob_async", "bob@example.com", "Hello World"))
```

## Repository Pattern

Wrap the adapter in a repository class to separate data access from domain logic.

```python
import logging
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.adapters.base.sqlalchemy.ports import SQLAlchemyPort
from archipy.models.dtos.pagination_dto import PaginationDTO
from archipy.models.dtos.sort_dto import SortDTO
from archipy.models.errors import DatabaseQueryError, NotFoundError
from archipy.models.types.base_types import SortOrderType

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User entities backed by PostgreSQL.

    Args:
        adapter: SQLAlchemy port implementation to use.
    """

    def __init__(self, adapter: SQLAlchemyPort) -> None:
        self._adapter = adapter

    def save(self, user: User) -> User:
        """Persist a user.

        Args:
            user: User entity to save.

        Returns:
            The saved User with DB-populated fields.

        Raises:
            DatabaseQueryError: If the database operation fails.
        """
        try:
            return self._adapter.create(user)
        except DatabaseQueryError as e:
            logger.error(f"Failed to save user: {e}")
            raise

    def get(self, user_id: UUID) -> User:
        """Retrieve a user by UUID.

        Args:
            user_id: UUID to look up.

        Returns:
            The matching User entity.

        Raises:
            NotFoundError: If not found.
            DatabaseQueryError: If the database operation fails.
        """
        try:
            user = self._adapter.get_by_uuid(User, user_id)
        except DatabaseQueryError as e:
            logger.error(f"Failed to fetch user {user_id}: {e}")
            raise

        if user is None:
            raise NotFoundError()
        return user

    def find_by_username(self, username: str) -> User | None:
        """Find a user by username.

        Args:
            username: Username to search for.

        Returns:
            Matching User or ``None`` if not found.

        Raises:
            DatabaseQueryError: If the database operation fails.
        """
        query = select(User).where(User.username == username)
        try:
            result = self._adapter.scalars(query)
            return result.first()
        except DatabaseQueryError as e:
            logger.error(f"Failed to find user by username={username}: {e}")
            raise

    def list_paginated(self, page: int = 1, page_size: int = 20) -> tuple[Sequence[User], int]:
        """List users with pagination.

        Args:
            page: 1-based page number.
            page_size: Results per page.

        Returns:
            Tuple of (users list, total count).

        Raises:
            DatabaseQueryError: If the query fails.
        """
        pagination = PaginationDTO(page=page, page_size=page_size)
        sort_info = SortDTO(field=User.username, order=SortOrderType.ASCENDING)
        try:
            return self._adapter.execute_search_query(
                entity=User,
                query=select(User),
                pagination=pagination,
                sort_info=sort_info,
            )
        except DatabaseQueryError as e:
            logger.error(f"Paginated list failed: {e}")
            raise


# Usage
repo = UserRepository(PostgresSQLAlchemyAdapter())

user = repo.save(User(username="alice", email="alice@example.com"))
found = repo.get(user.uuid)
logger.info(f"Found: {found.username}")

users, total = repo.list_paginated(page=1, page_size=10)
logger.info(f"Total users: {total}")
```

## Connection Pool Tuning

The default pool settings work for most applications, but you can tune them for your workload:

```python
from archipy.configs.config_template import PostgresSQLAlchemyConfig

# High-concurrency web API
api_config = PostgresSQLAlchemyConfig(
    HOST="localhost",
    PORT=5432,
    DATABASE="mydb",
    USERNAME="myuser",
    PASSWORD="secret",
    POOL_SIZE=20,  # Keep 20 persistent connections open
    POOL_MAX_OVERFLOW=10,  # Allow up to 10 additional overflow connections
    POOL_TIMEOUT=5,  # Fail fast if pool is exhausted (5 s)
    POOL_RECYCLE_SECONDS=300,  # Recycle connections every 5 min (avoids stale TCP)
    POOL_PRE_PING=True,  # Validate connections before use
    POOL_USE_LIFO=True,  # LIFO: reuse warm connections, keep cold ones idle
)

# Batch/worker process — smaller pool
worker_config = PostgresSQLAlchemyConfig(
    HOST="localhost",
    PORT=5432,
    DATABASE="mydb",
    USERNAME="myuser",
    PASSWORD="secret",
    POOL_SIZE=5,
    POOL_MAX_OVERFLOW=2,
    POOL_TIMEOUT=30,
)
```

## Troubleshooting

### `DatabaseConnectionError` on startup

- Verify `HOST`, `PORT`, `DATABASE`, `USERNAME`, and `PASSWORD` are correct.
- Confirm the PostgreSQL server is running: `pg_isready -h localhost -p 5432`.
- Check firewall rules if connecting to a remote host.
- When using SSL, ensure `sslmode` is included in the DSN if required.

### `DatabaseTransactionError` — serialisation failures

- Under high concurrency with `ISOLATION_LEVEL="SERIALIZABLE"`, serialisation failures are expected. Add a retry loop
  around your transaction.
- Downgrade to `"REPEATABLE READ"` (the ArchiPy default) if strong serialisation is not required.

### Pool exhaustion (`QueuePool limit exceeded`)

- Increase `POOL_SIZE` and/or `POOL_MAX_OVERFLOW`.
- Reduce transaction scope — avoid holding sessions open during slow external calls.
- Reduce `POOL_TIMEOUT` to fail fast and surface exhaustion early rather than queuing indefinitely.

### Stale connections (`OperationalError: server closed the connection`)

- Enable `POOL_PRE_PING=True` (the default) — SQLAlchemy will test each connection before issuing it.
- Reduce `POOL_RECYCLE_SECONDS` below any server or firewall idle-connection timeout (e.g., set to `300` if your load
  balancer drops connections idle for more than 5 minutes).

### Slow queries visible in logs

- Set `ECHO=True` during development to log all SQL statements.
- Set `HIDE_PARAMETERS=False` to see query parameter values.
- Use `QUERY_CACHE_SIZE=0` to disable the SQLAlchemy compiled-query cache if you suspect it is serving incorrect cached
  queries.

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — PostgreSQL configuration setup
- [BDD Testing](../testing_strategy.md) — Testing database operations
- [SQLAlchemy Decorators](../helpers/decorators.md#sqlalchemy-transaction-decorators) — Transaction decorator usage
- [API Reference](../../api_reference/adapters/postgres.md) — Full PostgreSQL adapter API documentation
