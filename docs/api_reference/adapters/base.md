# Base SQLAlchemy

The `base/sqlalchemy` subpackage provides the foundational SQLAlchemy components shared across all relational database adapters, including the abstract port interface, session managers, and session manager registries.

## ports

Abstract port interface defining the contract all SQLAlchemy-based adapters must fulfil.

::: archipy.adapters.base.sqlalchemy.ports
    options:
      show_root_heading: true
      show_source: true

## session_manager_ports

Abstract interface for SQLAlchemy session managers, decoupling session lifecycle from adapter logic.

::: archipy.adapters.base.sqlalchemy.session_manager_ports
    options:
      show_root_heading: true
      show_source: true

## session_manager_registry

Registry for tracking and resolving active session manager instances.

::: archipy.adapters.base.sqlalchemy.session_manager_registry
    options:
      show_root_heading: true
      show_source: true

## session_managers

Concrete session manager implementations that handle SQLAlchemy session creation, scoping, and teardown.

::: archipy.adapters.base.sqlalchemy.session_managers
    options:
      show_root_heading: true
      show_source: true

## adapters

The base SQLAlchemy adapter implements generic CRUD operations that concrete database adapters (PostgreSQL, SQLite, StarRocks) inherit from.

::: archipy.adapters.base.sqlalchemy.adapters
    options:
      show_root_heading: true
      show_source: true
