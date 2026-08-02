---
title: MySQL Adapter Tutorial
description: Practical examples for using the ArchiPy MySQL adapter.
---

# MySQL Adapter Tutorial

This example demonstrates how to use the MySQL adapter for database operations with proper exception handling and
Python 3.14 type hints.

## Installation

```bash
uv add "archipy[mysql]"
```

> **Tip:** For async support, also install `archipy[mysql-async,sqlalchemy-async]`.

## Configuration

Configure the MySQL adapter via environment variables or a `MySQLSQLAlchemyConfig` object.

### Environment Variables

```bash
MYSQL_SQLALCHEMY__HOST=localhost
MYSQL_SQLALCHEMY__PORT=3306
MYSQL_SQLALCHEMY__USERNAME=root
MYSQL_SQLALCHEMY__PASSWORD=password
MYSQL_SQLALCHEMY__DATABASE=app_db
MYSQL_SQLALCHEMY__POOL_SIZE=20
MYSQL_SQLALCHEMY__ECHO=false
```

### Direct Configuration

```python
from archipy.configs.config_template import MySQLSQLAlchemyConfig

config = MySQLSQLAlchemyConfig(
    HOST="localhost",
    PORT=3306,
    USERNAME="root",
    PASSWORD="password",
    DATABASE="app_db",
)
```

## Basic Usage

```python
import logging

from sqlalchemy import Column, String

from archipy.adapters.mysql.sqlalchemy.adapters import MySQLSQLAlchemyAdapter
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity
from archipy.models.errors import DatabaseConnectionError, DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)


# Define a model
class User(BaseEntity):
    __tablename__ = "users"
    username = Column(String(100), unique=True)
    email = Column(String(255), unique=True)


# Create adapter
try:
    adapter = MySQLSQLAlchemyAdapter()
except DatabaseConnectionError as e:
    logger.error(f"Failed to create adapter: {e}")
    raise
else:
    logger.info("MySQL adapter created successfully")

# Create tables
try:
    BaseEntity.metadata.create_all(adapter.session_manager.engine)
except DatabaseQueryError as e:
    logger.error(f"Failed to create tables: {e}")
    raise
else:
    logger.info("Database tables created")

# Basic operations
try:
    with adapter.get_session() as session:
        # Create
        user = User(username="john_doe", email="john@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        # Read
        from sqlalchemy import select
        stmt = select(User).where(User.username == "john_doe")
        found_user = session.execute(stmt).scalar_one_or_none()
        if found_user:
            logger.info(f"User email: {found_user.email}")  # john@example.com

            # Update
            found_user.email = "john.doe@example.com"
            session.commit()

            # Delete
            session.delete(found_user)
            session.commit()
except DatabaseQueryError as e:
    logger.error(f"Database operation failed: {e}")
    raise
except DatabaseConnectionError as e:
    logger.error(f"Database connection failed: {e}")
    raise
else:
    logger.info("All database operations completed successfully")
```

## Using Transactions

```python
import logging

from archipy.helpers.decorators.sqlalchemy_atomic import mysql_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)


@mysql_sqlalchemy_atomic_decorator
def create_user_with_profile(username: str, email: str, profile_data: dict[str, str]) -> User:
    """Create a user and profile in a single transaction.

    Args:
        username: User's username
        email: User's email address
        profile_data: Profile information dictionary

    Returns:
        Created user object

    Raises:
        DatabaseQueryError: If database operation fails
    """
    user = User(username=username, email=email)
    adapter.create(user)

    profile = Profile(user_id=user.uuid, **profile_data)  # type: ignore[name-defined]
    adapter.create(profile)

    logger.info(f"User and profile created: {username}")
    return user
```

## Async Operations

```python
import asyncio
import logging

from archipy.adapters.mysql.sqlalchemy.adapters import AsyncMySQLSQLAlchemyAdapter
from archipy.helpers.decorators.sqlalchemy_atomic import async_mysql_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseConnectionError, DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main async function demonstrating MySQL async operations."""
    try:
        adapter = AsyncMySQLSQLAlchemyAdapter()
    except DatabaseConnectionError as e:
        logger.error(f"Failed to create async adapter: {e}")
        raise
    else:
        logger.info("Async MySQL adapter created")

    @async_mysql_sqlalchemy_atomic_decorator
    async def create_user_async(username: str, email: str) -> User:
        """Create a user asynchronously.

        Args:
            username: User's username
            email: User's email address

        Returns:
            Created user object

        Raises:
            DatabaseQueryError: If database operation fails
        """
        try:
            user = User(username=username, email=email)
            result = await adapter.create(user)
        except DatabaseQueryError as e:
            logger.error(f"Failed to create user: {e}")
            raise
        else:
            logger.info(f"User created: {username}")
            return result

    try:
        user = await create_user_async("jane_doe", "jane@example.com")
    except (DatabaseQueryError, DatabaseConnectionError) as e:
        logger.error(f"Async operation failed: {e}")
        raise
    else:
        logger.info(f"Created user: {user.username}")  # jane_doe


# Run async operations
asyncio.run(main())
```

## Error Handling

```python
import logging
from uuid import UUID

from archipy.models.errors import (
    AlreadyExistsError,
    DatabaseConnectionError,
    DatabaseQueryError,
    NotFoundError,
)

# Configure logging
logger = logging.getLogger(__name__)


def get_user_by_id(user_id: UUID) -> User | None:
    """Get a user by their UUID.

    Args:
        user_id: User's unique identifier

    Returns:
        User object if found, None otherwise

    Raises:
        NotFoundError: If user doesn't exist
        DatabaseQueryError: If database query fails
        DatabaseConnectionError: If database connection fails
    """
    try:
        user = adapter.get_by_uuid(User, user_id)
    except (DatabaseQueryError, DatabaseConnectionError) as e:
        logger.error(f"Failed to get user: {e}")
        raise
    else:
        if not user:
            raise NotFoundError(
                resource_type="user",
                additional_data={"user_id": str(user_id)},
            )
        logger.info(f"User retrieved: {user.username}")
        return user
```

## Integration with FastAPI

```python
import logging
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from archipy.adapters.mysql.sqlalchemy.adapters import MySQLSQLAlchemyAdapter
from archipy.models.errors import AlreadyExistsError, DatabaseQueryError, NotFoundError

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()
adapter = MySQLSQLAlchemyAdapter()


class UserCreate(BaseModel):
    username: str
    email: EmailStr


class UserResponse(BaseModel):
    uuid: UUID
    username: str
    email: str


@app.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate) -> dict[str, str | UUID]:
    """Create a new user."""
    try:
        user = User(username=user_data.username, email=user_data.email)
        created_user = adapter.create(user)
    except AlreadyExistsError as e:
        logger.warning(f"User already exists: {user_data.username}")
        raise HTTPException(status_code=409, detail="User already exists") from e
    except DatabaseQueryError as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail="Database error") from e
    else:
        logger.info(f"User created: {user_data.username}")
        return {
            "uuid": created_user.uuid,
            "username": created_user.username,
            "email": created_user.email,
        }


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID) -> dict[str, str | UUID]:
    """Get a user by ID."""
    try:
        user = adapter.get_by_uuid(User, user_id)
    except DatabaseQueryError as e:
        logger.error(f"Database query failed: {e}")
        raise HTTPException(status_code=500, detail="Database error") from e
    else:
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"User retrieved: {user.username}")
        return {
            "uuid": user.uuid,
            "username": user.username,
            "email": user.email,
        }
```

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — MySQL configuration setup
- [BDD Testing](../testing_strategy.md) — Testing database operations
- [PostgreSQL Adapter](postgres.md) — Similar patterns for PostgreSQL
- [SQLAlchemy Decorators](../helpers/decorators.md#sqlalchemy-transaction-decorators) — Transaction decorator usage
- [API Reference](../../api_reference/adapters/mysql.md) — Full MySQL adapter API documentation
