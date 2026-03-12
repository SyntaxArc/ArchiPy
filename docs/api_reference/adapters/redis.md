# Redis

The `redis` adapter provides a complete Redis integration including the concrete adapter, its abstract port interface, and a mock implementation for testing.

## ports

Abstract port interface defining the Redis adapter contract.

::: archipy.adapters.redis.ports
    options:
      show_root_heading: true
      show_source: true

## adapters

Concrete Redis adapter wrapping the Redis client with ArchiPy conventions for cache operations, pub/sub, and key-value management.

::: archipy.adapters.redis.adapters
    options:
      show_root_heading: true
      show_source: true

## mocks

In-memory mock implementation of the Redis port for use in unit tests and BDD scenarios.

::: archipy.adapters.redis.mocks
    options:
      show_root_heading: true
      show_source: true
