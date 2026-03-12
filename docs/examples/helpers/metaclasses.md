# Metaclass Examples

This page demonstrates how to use ArchiPy's metaclasses for advanced Python patterns with proper type hints and error handling.

## Singleton Metaclass

The Singleton metaclass ensures that only one instance of a class exists throughout the application lifecycle.

### Basic Usage

```python
import logging

from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)


# Create a singleton class
class Database(metaclass=Singleton):
    """Database connection singleton.

    Only one instance of this class will exist, ensuring a single
    database connection pool across the application.
    """

    def __init__(self, connection_string: str | None = None) -> None:
        """Initialize database connection.

        Args:
            connection_string: Database connection URL

        Raises:
            ConfigurationError: If connection string is invalid
        """
        if connection_string is None and not hasattr(self, "connection_string"):
            raise ConfigurationError()

        if connection_string:
            self.connection_string = connection_string
            logger.info(f"Database initialized with: {connection_string}")

    def query(self, sql: str) -> list[dict[str, str]]:
        """Execute a SQL query.

        Args:
            sql: SQL query string

        Returns:
            Query results
        """
        logger.debug(f"Executing query: {sql}")
        # Execute query logic here
        return []


# Usage
try:
    db1 = Database("postgresql://localhost:5432/mydb")
except ConfigurationError as e:
    logger.error(f"Failed to create database instance: {e}")
    raise
else:
    logger.info("First database instance created")

# Subsequent calls return the same instance
db2 = Database()  # No new instance created

logger.info(f"Same instance: {db1 is db2}")  # True
logger.info(f"Connection string: {db2.connection_string}")  # "postgresql://localhost:5432/mydb"
```

### Configuration Manager Example

```python
import logging
from typing import Any

from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)


class ConfigurationManager(metaclass=Singleton):
    """Application configuration manager singleton.

    Ensures consistent configuration access across the application.
    """

    def __init__(self, config_file: str | None = None) -> None:
        """Initialize configuration manager.

        Args:
            config_file: Path to configuration file

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        self._config: dict[str, Any] = {}
        if config_file and not hasattr(self, "_loaded"):
            try:
                self._config = self._load_config(config_file)
                self._loaded = True
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                raise ConfigurationError() from e
            else:
                logger.info(f"Configuration loaded from: {config_file}")

    def _load_config(self, config_file: str) -> dict[str, Any]:
        """Load configuration from file.

        Args:
            config_file: Path to configuration file

        Returns:
            Configuration dictionary
        """
        # Load config logic here
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
        logger.debug(f"Configuration updated: {key} = {value}")


# Usage
try:
    config = ConfigurationManager("/path/to/config.yaml")
except ConfigurationError as e:
    logger.error(f"Configuration initialization failed: {e}")
    raise
else:
    logger.info("Configuration manager initialized")

# Access from anywhere in the application
config_instance = ConfigurationManager()  # Returns the same instance
database_url = config_instance.get("database_url", "sqlite:///default.db")
logger.info(f"Database URL: {database_url}")
```

### Connection Pool Example

```python
import logging
from typing import Any

from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError

# Configure logging
logger = logging.getLogger(__name__)


class ConnectionPool(metaclass=Singleton):
    """Database connection pool singleton.

    Manages a pool of database connections efficiently.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        pool_size: int = 10
    ) -> None:
        """Initialize connection pool.

        Args:
            host: Database host
            port: Database port
            database: Database name
            pool_size: Maximum number of connections

        Raises:
            DatabaseConnectionError: If pool initialization fails
        """
        if host and not hasattr(self, "_pool"):
            try:
                self.host = host
                self.port = port or 5432
                self.database = database
                self.pool_size = pool_size
                self._pool = self._create_pool()
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise DatabaseConnectionError() from e
            else:
                logger.info(f"Connection pool created: {pool_size} connections")

    def _create_pool(self) -> list[Any]:
        """Create the connection pool.

        Returns:
            List of database connections
        """
        # Create pool logic here
        return []

    def get_connection(self) -> Any:
        """Get a connection from the pool.

        Returns:
            Database connection

        Raises:
            DatabaseConnectionError: If no connections available
        """
        try:
            if not self._pool:
                raise DatabaseConnectionError()
            connection = self._pool.pop()
        except IndexError as e:
            logger.error("Connection pool exhausted")
            raise DatabaseConnectionError() from e
        else:
            logger.debug("Connection acquired from pool")
            return connection

    def release_connection(self, connection: Any) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Database connection to release
        """
        self._pool.append(connection)
        logger.debug("Connection released to pool")


# Usage
try:
    pool = ConnectionPool(
        host="localhost",
        port=5432,
        database="myapp",
        pool_size=20
    )
except DatabaseConnectionError as e:
    logger.error(f"Failed to initialize connection pool: {e}")
    raise
else:
    logger.info("Connection pool ready")

# Get connection from anywhere
try:
    conn = pool.get_connection()
except DatabaseConnectionError as e:
    logger.error(f"Failed to get connection: {e}")
    raise
else:
    # Use connection
    logger.info("Using database connection")

    # Release connection
    pool.release_connection(conn)
    logger.info("Connection released")
```

## Best Practices

### Thread Safety Considerations

```python
import logging
import threading

from archipy.helpers.metaclasses.singleton import Singleton

# Configure logging
logger = logging.getLogger(__name__)


class ThreadSafeCounter(metaclass=Singleton):
    """Thread-safe counter using singleton pattern.

    Demonstrates thread safety with singleton metaclass.
    """

    def __init__(self) -> None:
        """Initialize counter with thread lock."""
        if not hasattr(self, "_count"):
            self._count = 0
            self._lock = threading.Lock()
            logger.info("Thread-safe counter initialized")

    def increment(self) -> int:
        """Increment counter in thread-safe manner.

        Returns:
            New counter value
        """
        with self._lock:
            self._count += 1
            new_value = self._count
        logger.debug(f"Counter incremented to: {new_value}")
        return new_value

    def get_value(self) -> int:
        """Get current counter value.

        Returns:
            Current counter value
        """
        with self._lock:
            return self._count


# Usage in multi-threaded environment
counter = ThreadSafeCounter()

def worker() -> None:
    """Worker thread that increments counter."""
    for _ in range(100):
        counter.increment()

# Create multiple threads
threads = [threading.Thread(target=worker) for _ in range(10)]

# Start all threads
for thread in threads:
    thread.start()

# Wait for completion
for thread in threads:
    thread.join()

logger.info(f"Final count: {counter.get_value()}")  # Should be 1000
```

## Common Pitfalls

### Avoid Multiple Initializations

```python
import logging

from archipy.helpers.metaclasses.singleton import Singleton

# Configure logging
logger = logging.getLogger(__name__)


class BadSingleton(metaclass=Singleton):
    """Example of what NOT to do with singleton."""

    def __init__(self, value: str) -> None:
        """This will only run on first instantiation!"""
        self.value = value
        logger.warning(f"Initializing with value: {value}")


# First call
instance1 = BadSingleton("first")
logger.info(f"Instance1 value: {instance1.value}")  # "first"

# Second call - __init__ is NOT called again!
instance2 = BadSingleton("second")
logger.info(f"Instance2 value: {instance2.value}")  # Still "first"!
logger.info(f"Same instance: {instance1 is instance2}")  # True


# BETTER: Check if already initialized
class GoodSingleton(metaclass=Singleton):
    """Proper singleton implementation."""

    def __init__(self, value: str | None = None) -> None:
        """Initialize only if not already initialized."""
        if not hasattr(self, "value") and value:
            self.value = value
            logger.info(f"Initialized with value: {value}")
        elif value:
            logger.warning(f"Already initialized, ignoring new value: {value}")
```

## See Also

- [Decorators](decorators.md) - Other helper decorators
- [Utils](utils.md) - Utility functions
- [API Reference](../../api_reference/helpers/index.md) - Full metaclasses API documentation
