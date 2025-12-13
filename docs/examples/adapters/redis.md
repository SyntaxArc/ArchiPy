# Redis Adapter Examples

This guide demonstrates how to use the ArchiPy Redis adapter for common caching and key-value storage patterns.

## Basic Usage

### Installation

First, ensure you have the Redis dependencies installed:

```bash
pip install "archipy[redis]"
# or
uv add "archipy[redis]"
```

### Synchronous Redis Adapter

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Create a Redis adapter with connection details
    redis = RedisAdapter(
        host="localhost",
        port=6379,
        db=0,
        password=None  # Optional
    )

    # Set and get values
    redis.set("user:123:name", "John Doe")
    name = redis.get("user:123:name")
    logger.info(f"User name: {name}")  # Output: User name: John Doe

    # Set with expiration (seconds)
    redis.set("session:456", "active", ex=3600)  # Expires in 1 hour

    # Delete a key
    redis.delete("user:123:name")

    # Check if key exists
    if redis.exists("session:456"):
        logger.info("Session exists")
except CacheError as e:
    logger.error(f"Redis operation failed: {e}")
    raise
```

### Asynchronous Redis Adapter

```python
import asyncio
import logging

from archipy.adapters.redis.adapters import AsyncRedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        # Create an async Redis adapter
        redis = AsyncRedisAdapter(
            host="localhost",
            port=6379,
            db=0
        )

        # Async operations
        await redis.set("counter", "1")
        await redis.incr("counter")  # Increment
        count = await redis.get("counter")
        logger.info(f"Counter: {count}")  # Output: Counter: 2

        # Cleanup
        await redis.close()
    except CacheError as e:
        logger.error(f"Redis operation failed: {e}")
        raise


# Run the async function
asyncio.run(main())
```

## Caching Patterns

### Function Result Caching

```python
import json
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError, CacheMissError

# Configure logging
logger = logging.getLogger(__name__)

# Define a type variable for generic function types
T = TypeVar('T', bound=Callable[..., Any])

# Create a Redis adapter
redis = RedisAdapter(host="localhost", port=6379, db=0)


def cache_result(key_prefix: str, ttl: int = 300) -> Callable[[T], T]:
    """Decorator to cache function results in Redis.

    Args:
        key_prefix: Prefix for the Redis cache key
        ttl: Time-to-live in seconds (default: 5 minutes)

    Returns:
        Decorated function with Redis caching
    """

    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create a cache key with function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            try:
                # Try to get from cache
                cached = redis.get(cache_key)
                if cached:
                    return json.loads(cached)

                # Execute function and cache result
                result = func(*args, **kwargs)
                redis.set(cache_key, json.dumps(result), ex=ttl)
                return result
            except CacheMissError:
                # Execute function if not in cache
                result = func(*args, **kwargs)
                try:
                    redis.set(cache_key, json.dumps(result), ex=ttl)
                except CacheError as e:
                    # Log but don't fail if caching fails
                    logger.warning(f"Failed to cache result: {e}")
                return result
            except CacheError as e:
                # Execute function if Redis fails
                logger.warning(f"Redis error: {e}")
                return func(*args, **kwargs)

        return cast(T, wrapper)

    return decorator


# Example usage
@cache_result("api", ttl=60)
def expensive_api_call(item_id: int) -> dict[str, str | int]:
    """Simulate an expensive API call.

    Args:
        item_id: ID of the item to fetch

    Returns:
        Item data dictionary
    """
    logger.info("Executing expensive operation...")
    time.sleep(1)  # Simulate expensive operation
    return {"id": item_id, "name": f"Item {item_id}", "data": "Some data"}


# First call will execute the function
result1 = expensive_api_call(123)
logger.info(f"First call: {result1}")

# Second call will retrieve from cache
result2 = expensive_api_call(123)
logger.info(f"Second call: {result2}")
```

## Mock Redis for Testing

ArchiPy provides a Redis mock for unit testing that doesn't require a real Redis server:

```python
import logging
import unittest

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.adapters.redis.mocks import RedisMock
from archipy.models.errors import CacheError, CacheMissError

# Configure logging
logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, redis_adapter: RedisAdapter) -> None:
        self.redis = redis_adapter

    def get_user(self, user_id: int) -> str:
        """Get user data, either from cache or backend.

        Args:
            user_id: User ID to look up

        Returns:
            User data as a string

        Raises:
            CacheError: If Redis operation fails
        """
        try:
            cache_key = f"user:{user_id}"
            cached = self.redis.get(cache_key)
            if cached:
                return cached

            # In real code, we'd fetch from database if not in cache
            user_data = f"User {user_id} data"
            self.redis.set(cache_key, user_data, ex=300)
            return user_data
        except CacheMissError:
            # Handle cache miss
            user_data = f"User {user_id} data"
            try:
                self.redis.set(f"user:{user_id}", user_data, ex=300)
            except CacheError:
                pass  # Ignore error setting cache
            return user_data


class TestUserService(unittest.TestCase):
    def setUp(self) -> None:
        # Use the RedisMock instead of a real Redis connection
        self.redis_mock = RedisMock()
        self.user_service = UserService(self.redis_mock)

    def test_get_user(self) -> None:
        # Test first fetch (not cached)
        user_data = self.user_service.get_user(123)
        self.assertEqual(user_data, "User 123 data")

        # Test that it was cached
        self.assertEqual(self.redis_mock.get("user:123"), "User 123 data")

        # Change the cached value to test cache hit
        self.redis_mock.set("user:123", "Modified data")

        # Test cached fetch
        user_data = self.user_service.get_user(123)
        self.assertEqual(user_data, "Modified data")


# Run the test
if __name__ == "__main__":
    unittest.main()
```

### Async Redis Mock

For async code, use the async variant:

```python
import asyncio
import logging
import unittest

from archipy.adapters.redis.adapters import AsyncRedisAdapter
from archipy.adapters.redis.mocks import AsyncRedisMock
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)


class AsyncUserService:
    def __init__(self, redis_adapter: AsyncRedisAdapter) -> None:
        self.redis = redis_adapter

    async def get_user(self, user_id: int) -> str:
        """Get user data asynchronously, either from cache or backend.

        Args:
            user_id: User ID to look up

        Returns:
            User data as a string

        Raises:
            CacheError: If Redis operation fails
        """
        try:
            cache_key = f"user:{user_id}"
            cached = await self.redis.get(cache_key)
        except CacheError as e:
            logger.error(f"Cache error: {e}")
            raise
        else:
            if cached:
                return cached

            # In real code, we'd fetch from database if not in cache
            user_data = f"User {user_id} data"
            try:
                await self.redis.set(cache_key, user_data, ex=300)
            except CacheError as e:
                logger.warning(f"Failed to cache user data: {e}")
            return user_data


class TestAsyncUserService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        # Use the AsyncRedisMock instead of a real Redis connection
        self.redis_mock = AsyncRedisMock()
        self.user_service = AsyncUserService(self.redis_mock)

    async def test_get_user(self) -> None:
        # Test first fetch (not cached)
        user_data = await self.user_service.get_user(123)
        self.assertEqual(user_data, "User 123 data")

        # Test that it was cached
        cached = await self.redis_mock.get("user:123")
        self.assertEqual(cached, "User 123 data")

        # Change the cached value to test cache hit
        await self.redis_mock.set("user:123", "Modified data")

        # Test cached fetch
        user_data = await self.user_service.get_user(123)
        self.assertEqual(user_data, "Modified data")


# Run the async test
if __name__ == "__main__":
    unittest.main()
```

## Advanced Redis Features

### Publish/Subscribe

```python
import logging
import threading
import time

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)


# Subscriber thread
def subscribe_thread() -> None:
    try:
        subscriber = RedisAdapter(host="localhost", port=6379, db=0)
        pubsub = subscriber.pubsub()

        def message_handler(message: dict[str, str]) -> None:
            if message["type"] == "message":
                logger.info(f"Received message: {message['data']}")

        pubsub.subscribe(**{"channel:notifications": message_handler})
        pubsub.run_in_thread(sleep_time=0.5)

        # Keep thread running for demo
        time.sleep(10)
        pubsub.close()
    except CacheError as e:
        logger.error(f"Redis subscription error: {e}")
        raise


try:
    # Start subscriber in background
    thread = threading.Thread(target=subscribe_thread)
    thread.start()

    # Wait for subscriber to initialize
    time.sleep(1)

    # Create publisher
    redis = RedisAdapter(host="localhost", port=6379, db=0)

    # Publish messages
    for i in range(5):
        message = f"Notification {i}"
        redis.publish("channel:notifications", message)
        time.sleep(1)

    # Wait for thread to complete
    thread.join()
except CacheError as e:
    logger.error(f"Redis publisher error: {e}")
    raise
except Exception as e:
    logger.error(f"General error: {e}")
    raise
```

### Pipeline for Multiple Operations

```python
import logging

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.models.errors import CacheError

# Configure logging
logger = logging.getLogger(__name__)

try:
    redis = RedisAdapter(host="localhost", port=6379, db=0)

    # Create a pipeline for atomic operations
    pipe = redis.pipeline()
    pipe.set("stats:visits", 0)
    pipe.set("stats:unique_users", 0)
    pipe.set("stats:conversion_rate", "0.0")
    pipe.execute()  # Execute all commands at once

    # Increment multiple counters atomically
    pipe = redis.pipeline()
    pipe.incr("stats:visits")
    pipe.incr("stats:unique_users")
    results: list[int] = pipe.execute()
    logger.info(f"Visits: {results[0]}, Unique users: {results[1]}")
except CacheError as e:
    logger.error(f"Redis pipeline error: {e}")
    raise
```

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - Redis configuration setup
- [BDD Testing](../bdd_testing.md) - Testing Redis operations
- [Redis Mock Feature](../../features/redis_mock.feature) - BDD test scenarios for Redis mock
- [Cache Decorator](../helpers/decorators.md#cache-decorator) - TTL cache decorator usage
- [API Reference](../../api_reference/adapters.md) - Full Redis adapter API documentation
