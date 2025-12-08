# SQLite Adapter

This example demonstrates how to use the SQLite adapter for database operations with proper exception handling and Python 3.14 type hints.

## Basic Usage

```python
import logging

from archipy.adapters.sqlite.sqlalchemy.adapters import SQLiteSQLAlchemyAdapter
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity
from archipy.models.errors import DatabaseQueryError, DatabaseConnectionError
from sqlalchemy import Column, String

# Configure logging
logger = logging.getLogger(__name__)


# Define a model
class User(BaseEntity):
    __tablename__ = "users"
    username = Column(String(100), unique=True)
    email = Column(String(255), unique=True)


# Create adapter
try:
    adapter = SQLiteSQLAlchemyAdapter()
except Exception as e:
    logger.error(f"Failed to create adapter: {e}")
    raise DatabaseConnectionError() from e
else:
    logger.info("SQLite adapter created successfully")

# Create tables
try:
    BaseEntity.metadata.create_all(adapter.session_manager.engine)
except Exception as e:
    logger.error(f"Failed to create tables: {e}")
    raise DatabaseQueryError() from e
else:
    logger.info("Database tables created")

# Basic operations
try:
    with adapter.session() as session:
        # Create
        user = User(username="john_doe", email="john@example.com")
        session.add(user)
        session.commit()

        # Read
        user = session.query(User).filter_by(username="john_doe").first()
        logger.info(f"User email: {user.email}")  # john@example.com

        # Update
        user.email = "john.doe@example.com"
        session.commit()

        # Delete
        session.delete(user)
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

from archipy.helpers.decorators.sqlalchemy_atomic import sqlite_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)


@sqlite_sqlalchemy_atomic_decorator
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
    try:
        user = User(username=username, email=email)
        adapter.create(user)

        profile = Profile(user_id=user.uuid, **profile_data)
        adapter.create(profile)
    except Exception as e:
        logger.error(f"Failed to create user with profile: {e}")
        raise DatabaseQueryError() from e
    else:
        logger.info(f"User and profile created: {username}")
        return user
```

## Async Operations

```python
import asyncio
import logging

from archipy.adapters.sqlite.sqlalchemy.adapters import AsyncSQLiteSQLAlchemyAdapter
from archipy.helpers.decorators.sqlalchemy_atomic import async_sqlite_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError, DatabaseConnectionError

# Configure logging
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main async function demonstrating SQLite async operations."""
    try:
        adapter = AsyncSQLiteSQLAlchemyAdapter()
    except Exception as e:
        logger.error(f"Failed to create async adapter: {e}")
        raise DatabaseConnectionError() from e
    else:
        logger.info("Async SQLite adapter created")

    @async_sqlite_sqlalchemy_atomic_decorator
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
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise DatabaseQueryError() from e
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
    NotFoundError,
    DatabaseQueryError,
    DatabaseConnectionError
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
                additional_data={"user_id": str(user_id)}
            )
        logger.info(f"User retrieved: {user.username}")
        return user


def create_user_safe(username: str, email: str) -> User:
    """Create a user with comprehensive error handling.

    Args:
        username: User's username
        email: User's email address

    Returns:
        Created user object

    Raises:
        AlreadyExistsError: If user already exists
        DatabaseQueryError: If database operation fails
    """
    try:
        user = User(username=username, email=email)
        result = adapter.create(user)
    except AlreadyExistsError as e:
        logger.warning(f"User already exists: {username}")
        raise
    except DatabaseQueryError as e:
        logger.error(f"Failed to create user: {e}")
        raise
    else:
        logger.info(f"User created successfully: {username}")
        return result
```

## Using with Context Manager

```python
import logging

from archipy.adapters.sqlite.sqlalchemy.adapters import SQLiteSQLAlchemyAdapter
from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

adapter = SQLiteSQLAlchemyAdapter()

try:
    # Use context manager for automatic session management
    with adapter.session() as session:
        # Create multiple users
        users = [
            User(username="user1", email="user1@example.com"),
            User(username="user2", email="user2@example.com"),
            User(username="user3", email="user3@example.com"),
        ]

        for user in users:
            session.add(user)

        session.commit()

        # Query users
        all_users = session.query(User).all()
        logger.info(f"Created {len(all_users)} users")

except DatabaseQueryError as e:
    logger.error(f"Batch operation failed: {e}")
    raise
else:
    logger.info("Batch operation completed successfully")
```

## Integration with FastAPI

```python
import logging
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from archipy.adapters.sqlite.sqlalchemy.adapters import SQLiteSQLAlchemyAdapter
from archipy.models.errors import NotFoundError, AlreadyExistsError, DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()
adapter = SQLiteSQLAlchemyAdapter()


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
            "email": created_user.email
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
            "email": user.email
        }
```

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - SQLite configuration setup
- [BDD Testing](../bdd_testing.md) - Testing database operations
- [PostgreSQL Adapter](postgres.md) - Similar patterns for PostgreSQL
- [SQLAlchemy Decorators](../helpers/decorators.md#sqlalchemy-transaction-decorators) - Transaction decorator usage
- [API Reference](../../api_reference/adapters.md) - Full SQLite adapter API documentation
