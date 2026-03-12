# PostgreSQL

The `postgres/sqlalchemy` adapter provides a PostgreSQL-specific SQLAlchemy integration, including a concrete adapter, session manager, and session manager registry that extend the base SQLAlchemy components.

## Session Managers

PostgreSQL-specific session manager handling connection pooling and lifecycle for PostgreSQL databases.

::: archipy.adapters.postgres.sqlalchemy.session_managers
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## Session Manager Registry

Registry for PostgreSQL session manager instances.

::: archipy.adapters.postgres.sqlalchemy.session_manager_registry
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3

## Adapters

Concrete PostgreSQL adapter built on top of the base SQLAlchemy adapter with PostgreSQL-specific configuration.

::: archipy.adapters.postgres.sqlalchemy.adapters
    options:
      show_source: true
      show_root_toc_entry: false
      heading_level: 3
