# StarRocks

The `starrocks/sqlalchemy` adapter provides integration with StarRocks, a high-performance analytical database compatible with the MySQL protocol, using SQLAlchemy.

## session_managers

StarRocks-specific session manager handling connection management for the StarRocks analytical engine.

::: archipy.adapters.starrocks.sqlalchemy.session_managers
    options:
      show_root_heading: true
      show_source: true

## session_manager_registry

Registry for StarRocks session manager instances.

::: archipy.adapters.starrocks.sqlalchemy.session_manager_registry
    options:
      show_root_heading: true
      show_source: true

## adapters

Concrete StarRocks adapter built on the base SQLAlchemy adapter with StarRocks-specific dialect configuration.

::: archipy.adapters.starrocks.sqlalchemy.adapters
    options:
      show_root_heading: true
      show_source: true
