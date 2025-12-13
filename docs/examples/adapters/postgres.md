# PostgreSQL Adapter

This example demonstrates how to use the PostgreSQL adapter for database operations.

## Basic Usage

```python
import logging
from uuid import UUID

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
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
adapter = PostgresSQLAlchemyAdapter()

# Create tables
BaseEntity.metadata.create_all(adapter.session_manager.engine)

# Basic operations
try:
    # Get session
    session = adapter.get_session()

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
except (DatabaseQueryError, DatabaseConnectionError) as e:
    # The adapter's SQLAlchemyExceptionHandlerMixin will handle
    # and convert common exceptions to application-specific ones
    # These will already preserve the original error context with `from e`
    logger.error(f"Database operation failed: {e}")
    raise
```

## Using Transactions

```python
from archipy.helpers.decorators.sqlalchemy_atomic import postgres_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError, AlreadyExistsError


@postgres_sqlalchemy_atomic_decorator
def create_user_with_profile(username: str, email: str, profile_data: dict[str, str]) -> User:
    """Create a user and associated profile in a transaction.

    If any part fails, the entire transaction is rolled back.

    Args:
        username: User's username
        email: User's email
        profile_data: Dictionary of profile data

    Returns:
        User: The created user object

    Raises:
        DatabaseQueryError: If a database error occurs
        AlreadyExistsError: If the user or profile already exists
    """
    try:
        # Create user
        user = User(username=username, email=email)
        adapter.create(user)

        # Create profile with user's UUID
        profile = Profile(user_id=user.uuid, **profile_data)
        adapter.create(profile)
    except Exception as e:
        # The decorator will automatically handle the transaction,
        # rolling back on error and converting exceptions
        raise DatabaseQueryError() from e
    else:
        return user
```

## Async Operations

```python
import asyncio
import logging
from uuid import UUID

from archipy.adapters.postgres.sqlalchemy.adapters import AsyncPostgresSQLAlchemyAdapter
from archipy.helpers.decorators.sqlalchemy_atomic import async_postgres_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseConnectionError, DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)


async def main() -> None:
    adapter = AsyncPostgresSQLAlchemyAdapter()

    @async_postgres_sqlalchemy_atomic_decorator
    async def create_user_async(username: str, email: str) -> User:
        """Create a user asynchronously within a transaction.

        Args:
            username: User's username
            email: User's email

        Returns:
            User: The created user object

        Raises:
            DatabaseQueryError: If a database error occurs
            DatabaseConnectionError: If a connection error occurs
        """
        try:
            user = User(username=username, email=email)
            result = await adapter.create(user)
        except Exception as e:
            raise DatabaseQueryError() from e
        else:
            return result

    try:
        user = await create_user_async("jane_doe", "jane@example.com")
    except (DatabaseConnectionError, DatabaseQueryError) as e:
        logger.error(f"Database error: {e}")
        raise
    else:
        logger.info(f"User created: {user.username}")  # jane_doe
        return user
```

## Error Handling

```python
import logging
from uuid import UUID

from archipy.models.errors import (
    AlreadyExistsError,
    NotFoundError,
    DatabaseConnectionError,
    DatabaseQueryError
)

# Configure logging
logger = logging.getLogger(__name__)


def get_user_by_id(user_id: UUID) -> User | None:
    """Get a user by their UUID.

    Args:
        user_id: User UUID to look up

    Returns:
        User or None: The found user or None if not found

    Raises:
        NotFoundError: If user doesn't exist
        DatabaseConnectionError: If database connection fails
        DatabaseQueryError: For other database errors
    """
    try:
        user = adapter.get_by_uuid(User, user_id)
    except (DatabaseConnectionError, DatabaseQueryError) as e:
        # The adapter's exception handler will have already
        # converted common exceptions with proper chaining
        logger.error(f"Database error: {e}")
        raise
    else:
        if not user:
            raise NotFoundError(
                resource_type="user",
                additional_data={"user_id": str(user_id)}
            )
        return user
```

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - PostgreSQL configuration setup
- [BDD Testing](../bdd_testing.md) - Testing database operations
- [Atomic Transactions](../../features/atomic_transactions.feature) - BDD test scenarios for transactions
- [SQLAlchemy Decorators](../helpers/decorators.md#sqlalchemy-transaction-decorators) - Transaction decorator usage
- [API Reference](../../api_reference/adapters.md) - Full PostgreSQL adapter API documentation
