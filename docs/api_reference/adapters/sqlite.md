# SQLite

The `sqlite/sqlalchemy` adapter provides a SQLite-specific SQLAlchemy integration suitable for development, testing, and lightweight production workloads.

## session_managers

SQLite-specific session manager handling file-based and in-memory database connections.

::: archipy.adapters.sqlite.sqlalchemy.session_managers
    options:
      show_root_heading: true
      show_source: true

## session_manager_registry

Registry for SQLite session manager instances.

::: archipy.adapters.sqlite.sqlalchemy.session_manager_registry
    options:
      show_root_heading: true
      show_source: true

## adapters

Concrete SQLite adapter built on the base SQLAlchemy adapter with SQLite-specific configuration.

::: archipy.adapters.sqlite.sqlalchemy.adapters
    options:
      show_root_heading: true
      show_source: true
