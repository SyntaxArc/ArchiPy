# PostgreSQL

The `postgres/sqlalchemy` adapter provides a PostgreSQL-specific SQLAlchemy integration, including a concrete adapter, session manager, and session manager registry that extend the base SQLAlchemy components.

## session_managers

PostgreSQL-specific session manager handling connection pooling and lifecycle for PostgreSQL databases.

::: archipy.adapters.postgres.sqlalchemy.session_managers
    options:
      show_root_heading: true
      show_source: true

## session_manager_registry

Registry for PostgreSQL session manager instances.

::: archipy.adapters.postgres.sqlalchemy.session_manager_registry
    options:
      show_root_heading: true
      show_source: true

## adapters

Concrete PostgreSQL adapter built on top of the base SQLAlchemy adapter with PostgreSQL-specific configuration.

::: archipy.adapters.postgres.sqlalchemy.adapters
    options:
      show_root_heading: true
      show_source: true
