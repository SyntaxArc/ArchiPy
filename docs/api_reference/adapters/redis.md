---
title: Redis
description: API reference for the Redis adapter ports, adapters, RediSearch handles, and mocks.
---

# Redis

The `redis` adapter provides a complete Redis integration including the concrete adapter, its abstract port interface,
index-bound RediSearch handles, and a mock implementation for testing.

## Ports

Abstract port interface defining the Redis adapter contract.

::: archipy.adapters.redis.ports
options:
show_root_toc_entry: false
heading_level: 3

## Adapters

Concrete Redis adapter wrapping the Redis client with ArchiPy conventions for cache operations, pub/sub, and key-value
management.

::: archipy.adapters.redis.adapters
options:
show_root_toc_entry: false
heading_level: 3

## Search Ports

Abstract port interfaces for index-bound RediSearch operations (sync and async).

::: archipy.adapters.redis.search_ports
options:
show_root_toc_entry: false
heading_level: 3

## Search Adapters

Concrete RediSearch handle implementations, plus `pack_vector()` and `unpack_vector()` helpers for float32 vector
encoding. Supports `FLAT`, `HNSW`, and `SVS-VAMANA` vector indexes, KNN and `VECTOR_RANGE` queries, and runtime
tuning parameters including cluster `shard_k_ratio`.

::: archipy.adapters.redis.search
options:
show_root_toc_entry: false
heading_level: 3

## Mocks

In-memory mock implementation of the Redis port for use in unit tests and BDD scenarios.

::: archipy.adapters.redis.mocks
options:
show_root_toc_entry: false
heading_level: 3
