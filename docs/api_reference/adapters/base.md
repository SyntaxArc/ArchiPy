---
title: Base SQLAlchemy
description: API reference for the base SQLAlchemy adapter ports, session managers, and registry.
---

# Base SQLAlchemy

The `base/sqlalchemy` subpackage provides the foundational SQLAlchemy components shared across all relational database adapters, including the abstract port interface, session managers, and session manager registries.

## Ports

Abstract port interface defining the contract all SQLAlchemy-based adapters must fulfil.

::: archipy.adapters.base.sqlalchemy.ports
    options:
      show_root_toc_entry: false
      heading_level: 3

## Session Manager Ports

Abstract interface for SQLAlchemy session managers, decoupling session lifecycle from adapter logic.

::: archipy.adapters.base.sqlalchemy.session_manager_ports
    options:
      show_root_toc_entry: false
      heading_level: 3

## Session Manager Registry

Registry for tracking and resolving active session manager instances.

::: archipy.adapters.base.sqlalchemy.session_manager_registry
    options:
      show_root_toc_entry: false
      heading_level: 3

## Session Managers

Concrete session manager implementations that handle SQLAlchemy session creation, scoping, and teardown.

::: archipy.adapters.base.sqlalchemy.session_managers
    options:
      show_root_toc_entry: false
      heading_level: 3

## Adapters

The base SQLAlchemy adapter implements generic CRUD operations that concrete database adapters (PostgreSQL, SQLite, StarRocks) inherit from.

::: archipy.adapters.base.sqlalchemy.adapters
    options:
      show_root_toc_entry: false
      heading_level: 3
