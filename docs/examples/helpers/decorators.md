# Decorator Examples

This page demonstrates how to use ArchiPy's decorators for common cross-cutting concerns.

## Retry Decorator

The retry decorator automatically retries a function when it encounters specific exceptions.

```python
import logging
import random

from archipy.helpers.decorators.retry import retry_decorator
from archipy.models.errors import ResourceExhaustedError
from archipy.models.types.language_type import LanguageType

# Configure logging
logger = logging.getLogger(__name__)


# Retry a function that might fail temporarily
@retry_decorator(
    max_retries=3,
    delay=1,
    retry_on=(ConnectionError, TimeoutError),
    ignore=(ValueError,),
    resource_type="API",
    lang=LanguageType.EN
)
def unreliable_api_call(item_id: int) -> dict[str, Any]:
    """Make an API call that might fail temporarily.

    Args:
        item_id: The ID of the item to fetch

    Returns:
        API response data

    Raises:
        ResourceExhaustedError: If retries are exhausted
        ValueError: If input validation fails (not retried)
    """
    if item_id < 0:
        # This error won't be retried because it's in the ignored list
        raise ValueError("Item ID must be positive")

    # Simulate random failures
    if random.random() < 0.7:
        # This will be retried because ConnectionError is in retry_on
        raise ConnectionError("Temporary network issue")

    # Success case
    return {"id": item_id, "name": f"Item {item_id}"}


try:
    # This call might succeed after retries
    result = unreliable_api_call(42)
except ResourceExhaustedError as e:
    # This happens when all retries fail
    logger.error(f"All retry attempts failed: {e}")
    raise
except ValueError as e:
    # This happens for input validation failures (not retried)
    logger.error(f"Validation error: {e}")
    raise
else:
    logger.info(f"Request succeeded: {result}")
```

## Timeout Decorator

The timeout decorator ensures a function doesn't run longer than a specified duration.

```python
import logging
import time

from archipy.helpers.decorators.timeout import timeout_decorator
from archipy.models.errors import DeadlineExceededError

# Configure logging
logger = logging.getLogger(__name__)


# Set a timeout for a potentially long-running function
@timeout_decorator(3)  # 3 seconds timeout
def slow_operation(duration: float) -> str:
    """A function that might take too long.

    Args:
        duration: How long to run in seconds

    Returns:
        Completion message

    Raises:
        DeadlineExceededError: If function takes longer than the timeout
    """
    time.sleep(duration)  # Simulate work
    return "Operation completed"


try:
    # This will succeed because it completes within the timeout
    result = slow_operation(2)
except DeadlineExceededError as e:
    logger.error(f"Operation timed out: {e}")
    raise
else:
    logger.info(result)  # "Operation completed"

try:
    # This will raise a DeadlineExceededError because it exceeds the timeout
    result = slow_operation(5)
except DeadlineExceededError as e:
    logger.error(f"Operation timed out: {e}")
    # Expected to timeout
else:
    logger.info("This won't be reached")
```

## Timing Decorator

The timing decorator measures and logs the execution time of functions.

```python
import logging
import time

from archipy.helpers.decorators.timing import timing_decorator

# Configure logging
logger = logging.getLogger(__name__)


# Measure and log how long a function takes to execute
@timing_decorator
def process_data(items: list[int]) -> int:
    """Process a list of items with time measurement.

    Args:
        items: List of items to process

    Returns:
        Sum of processed items
    """
    time.sleep(0.1)  # Simulate processing time
    return sum(items)


# This will log the execution time before returning
result = process_data(list(range(100)))
logger.info(f"Result: {result}")  # Output: Result: 4950
# The decorator will log something like:
# INFO - Function 'process_data' executed in 0.103 seconds
```

## Cache Decorator

The TTL cache decorator caches function results with automatic expiration.

```python
import logging
import time

from archipy.helpers.decorators import ttl_cache_decorator

# Configure logging
logger = logging.getLogger(__name__)


# Cache the results of an expensive function
@ttl_cache_decorator(ttl_seconds=60, maxsize=100)
def fetch_user_data(user_id: int) -> dict[str, str | int]:
    """Fetch user data from a slow source with caching.

    Args:
        user_id: User ID to fetch

    Returns:
        User data dictionary
    """
    logger.info(f"Fetching data for user {user_id}...")
    time.sleep(1)  # Simulate slow API call
    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com"
    }


# First call - will execute the function and cache the result
start = time.time()
data1 = fetch_user_data(123)
logger.info(f"First call took {time.time() - start:.3f} seconds")

# Second call with same arguments - will use the cached result
start = time.time()
data2 = fetch_user_data(123)
logger.info(f"Second call took {time.time() - start:.3f} seconds")

# Different arguments - will execute the function
start = time.time()
data3 = fetch_user_data(456)
logger.info(f"Different user call took {time.time() - start:.3f} seconds")

# Clear the cache if needed
fetch_user_data.clear_cache()
```

## SQLAlchemy Transaction Decorators

These decorators automatically manage database transactions.

```python
import logging
from uuid import UUID

from archipy.helpers.decorators.sqlalchemy_atomic import postgres_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError, DatabaseConnectionError

# Configure logging
logger = logging.getLogger(__name__)


@postgres_sqlalchemy_atomic_decorator
def create_user(username: str, email: str) -> User:
    """Create a user in a database transaction.

    All database operations are wrapped in a transaction that
    will be automatically committed on success or rolled back on error.

    Args:
        username: User's username
        email: User's email address

    Returns:
        The created user object

    Raises:
        DatabaseQueryError: If the database operation fails
        DatabaseConnectionError: If the database connection fails
    """
    try:
        user = User(username=username, email=email)
        # Get session from the adapter injected by the decorator
        session = adapter.get_session()
        session.add(user)
    except Exception as e:
        # The decorator handles rolling back the transaction
        # and converting exceptions to appropriate types
        logger.error(f"Failed to create user: {e}")
        raise DatabaseQueryError() from e
    else:
        logger.info(f"User created: {username}")
        return user


# For async operations
from archipy.helpers.decorators.sqlalchemy_atomic import async_postgres_sqlalchemy_atomic_decorator


@async_postgres_sqlalchemy_atomic_decorator
async def update_user_email(user_id: UUID, new_email: str) -> User | None:
    """Update a user's email in an async transaction.

    Args:
        user_id: UUID of the user
        new_email: New email address

    Returns:
        Updated user or None if not found

    Raises:
        DatabaseQueryError: If the database operation fails
    """
    try:
        # Get async session from the adapter injected by the decorator
        session = adapter.get_session()
        user = await session.get(User, user_id)
    except Exception as e:
        # The decorator handles the error conversion and rollback
        logger.error(f"Failed to update user email: {e}")
        raise DatabaseQueryError() from e
    else:
        if not user:
            logger.warning(f"User not found: {user_id}")
            return None

        user.email = new_email
        logger.info(f"Updated email for user: {user_id}")
        return user
```
