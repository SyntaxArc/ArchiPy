# ScyllaDB

The `scylladb` adapter provides integration with ScyllaDB (and Apache Cassandra) for high-throughput, low-latency wide-column store operations.

## ports

Abstract port interface defining the ScyllaDB adapter contract.

::: archipy.adapters.scylladb.ports
    options:
      show_root_heading: true
      show_source: true

## adapters

Concrete ScyllaDB adapter implementing session management and query execution for ScyllaDB/Cassandra clusters.

::: archipy.adapters.scylladb.adapters
    options:
      show_root_heading: true
      show_source: true
