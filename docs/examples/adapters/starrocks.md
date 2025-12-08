# StarRocks Adapter

This example demonstrates how to use the StarRocks adapter for analytical database operations with proper exception handling and Python 3.14 type hints.

## Basic Usage

```python
import logging
from datetime import datetime

from archipy.adapters.starrocks.sqlalchemy.adapters import StarrocksSQLAlchemyAdapter
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity
from archipy.models.errors import DatabaseQueryError, DatabaseConnectionError
from sqlalchemy import Column, String, Integer, DateTime

# Configure logging
logger = logging.getLogger(__name__)


# Define a model
class User(BaseEntity):
    __tablename__ = "users"
    username = Column(String(100), unique=True)
    email = Column(String(255), unique=True)
    age = Column(Integer)
    created_at = Column(DateTime)


# Create adapter
try:
    adapter = StarrocksSQLAlchemyAdapter()
except Exception as e:
    logger.error(f"Failed to create adapter: {e}")
    raise DatabaseConnectionError() from e
else:
    logger.info("StarRocks adapter created successfully")

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
        user = User(
            username="john_doe",
            email="john@example.com",
            age=30,
            created_at=datetime.now()
        )
        session.add(user)
        session.commit()

        # Read
        user = session.query(User).filter_by(username="john_doe").first()
        logger.info(f"User email: {user.email}")  # john@example.com

        # Update
        user.age = 31
        session.commit()

        # Delete
        session.delete(user)
        session.commit()
except (DatabaseQueryError, DatabaseConnectionError) as e:
    logger.error(f"Database operation failed: {e}")
    raise
else:
    logger.info("All database operations completed successfully")
```

## Using Transactions

```python
import logging

from archipy.helpers.decorators.sqlalchemy_atomic import starrocks_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)


@starrocks_sqlalchemy_atomic_decorator
def create_user_with_profile(
    username: str,
    email: str,
    age: int,
    profile_data: dict[str, str]
) -> User:
    """Create a user and profile in a single transaction.

    Args:
        username: User's username
        email: User's email address
        age: User's age
        profile_data: Profile information dictionary

    Returns:
        Created user object

    Raises:
        DatabaseQueryError: If database operation fails
    """
    try:
        user = User(username=username, email=email, age=age)
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

from archipy.adapters.starrocks.sqlalchemy.adapters import AsyncStarrocksSQLAlchemyAdapter
from archipy.helpers.decorators.sqlalchemy_atomic import async_starrocks_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError, DatabaseConnectionError

# Configure logging
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main async function demonstrating StarRocks async operations."""
    try:
        adapter = AsyncStarrocksSQLAlchemyAdapter()
    except Exception as e:
        logger.error(f"Failed to create async adapter: {e}")
        raise DatabaseConnectionError() from e
    else:
        logger.info("Async StarRocks adapter created")

    @async_starrocks_sqlalchemy_atomic_decorator
    async def create_user_async(username: str, email: str, age: int) -> User:
        """Create a user asynchronously.

        Args:
            username: User's username
            email: User's email address
            age: User's age

        Returns:
            Created user object

        Raises:
            DatabaseQueryError: If database operation fails
        """
        try:
            user = User(username=username, email=email, age=age)
            result = await adapter.create(user)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise DatabaseQueryError() from e
        else:
            logger.info(f"User created: {username}")
            return result

    try:
        user = await create_user_async("jane_doe", "jane@example.com", 28)
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
```

## Advanced Queries

StarRocks is optimized for analytical queries. Here are some advanced patterns:

```python
import logging
from datetime import datetime, timedelta

from sqlalchemy import func

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Complex filtering for analytics
    recent_users = adapter.query(User).filter(
        User.age > 25,
        User.created_at >= datetime.now() - timedelta(days=30)
    ).all()
except DatabaseQueryError as e:
    logger.error(f"Failed to query recent users: {e}")
    raise
else:
    logger.info(f"Found {len(recent_users)} recent users")

try:
    # Aggregation for reporting
    age_stats = adapter.query(
        func.avg(User.age).label('avg_age'),
        func.max(User.age).label('max_age'),
        func.min(User.age).label('min_age')
    ).first()
except DatabaseQueryError as e:
    logger.error(f"Failed to compute age statistics: {e}")
    raise
else:
    logger.info(f"Age statistics: avg={age_stats.avg_age}, max={age_stats.max_age}, min={age_stats.min_age}")

try:
    # Joins for complex analytics
    from sqlalchemy import join

    user_profiles = adapter.query(User).join(
        Profile,
        User.uuid == Profile.user_id
    ).all()
except DatabaseQueryError as e:
    logger.error(f"Failed to join users and profiles: {e}")
    raise
else:
    logger.info(f"Retrieved {len(user_profiles)} user profiles")
```

## Batch Operations

StarRocks excels at batch operations for analytical workloads:

```python
import logging

from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Batch insert
    users = [
        User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            age=20 + i,
            created_at=datetime.now()
        )
        for i in range(1000)
    ]
    adapter.bulk_create(users)
except DatabaseQueryError as e:
    logger.error(f"Batch insert failed: {e}")
    raise
else:
    logger.info(f"Successfully inserted {len(users)} users")

try:
    # Batch update
    rows_updated = adapter.query(User).filter(User.age < 30).update(
        {"age": User.age + 1},
        synchronize_session=False
    )
except DatabaseQueryError as e:
    logger.error(f"Batch update failed: {e}")
    raise
else:
    logger.info(f"Updated {rows_updated} users")
```

## Configuration

```python
import logging

from archipy.configs.config_template import StarrocksConfig
from archipy.adapters.starrocks.sqlalchemy.adapters import StarrocksSQLAlchemyAdapter
from archipy.models.errors import ConfigurationError, DatabaseConnectionError

# Configure logging
logger = logging.getLogger(__name__)

# Configure StarRocks connection
try:
    config = StarrocksConfig(
        HOST="localhost",
        PORT=9030,
        USER="root",
        PASSWORD="password",
        DATABASE="analytics_db"
    )
except Exception as e:
    logger.error(f"Invalid configuration: {e}")
    raise ConfigurationError() from e
else:
    logger.info("StarRocks configuration created")

# Create adapter with custom config
try:
    adapter = StarrocksSQLAlchemyAdapter(config=config)
except Exception as e:
    logger.error(f"Failed to create adapter with config: {e}")
    raise DatabaseConnectionError() from e
else:
    logger.info("StarRocks adapter initialized with custom config")
```

## Integration with FastAPI

```python
import logging
from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from archipy.adapters.starrocks.sqlalchemy.adapters import StarrocksSQLAlchemyAdapter
from archipy.models.errors import NotFoundError, DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()
adapter = StarrocksSQLAlchemyAdapter()


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    age: int


class UserResponse(BaseModel):
    uuid: UUID
    username: str
    email: str
    age: int


@app.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate) -> dict[str, str | UUID | int]:
    """Create a new user for analytics."""
    try:
        user = User(
            username=user_data.username,
            email=user_data.email,
            age=user_data.age,
            created_at=datetime.now()
        )
        created_user = adapter.create(user)
    except DatabaseQueryError as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail="Database error") from e
    else:
        logger.info(f"User created: {user_data.username}")
        return {
            "uuid": created_user.uuid,
            "username": created_user.username,
            "email": created_user.email,
            "age": created_user.age
        }


@app.get("/analytics/age-distribution")
async def get_age_distribution() -> dict[str, list[dict[str, int]]]:
    """Get age distribution analytics."""
    try:
        from sqlalchemy import func

        distribution = adapter.query(
            User.age,
            func.count(User.uuid).label('count')
        ).group_by(User.age).order_by(User.age).all()
    except DatabaseQueryError as e:
        logger.error(f"Analytics query failed: {e}")
        raise HTTPException(status_code=500, detail="Query failed") from e
    else:
        result = [{"age": row.age, "count": row.count} for row in distribution]
        logger.info(f"Retrieved age distribution with {len(result)} groups")
        return {"distribution": result}
```

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - StarRocks configuration setup
- [BDD Testing](../bdd_testing.md) - Testing database operations
- [PostgreSQL Adapter](postgres.md) - Similar patterns for PostgreSQL
- [SQLAlchemy Decorators](../helpers/decorators.md#sqlalchemy-transaction-decorators) - Transaction decorator usage
- [API Reference](../../api_reference/adapters.md) - Full StarRocks adapter API documentation
