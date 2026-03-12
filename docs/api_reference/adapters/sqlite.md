---
title: SQLite
description: API reference for the SQLite adapter session managers and adapters.
---

# SQLite

The `sqlite/sqlalchemy` adapter provides a SQLite-specific SQLAlchemy integration suitable for development, testing, and
lightweight production workloads.

## Session Managers

SQLite-specific session manager handling file-based and in-memory database connections.

::: archipy.adapters.sqlite.sqlalchemy.session_managers
options:
show_root_toc_entry: false
heading_level: 3

## Session Manager Registry

Registry for SQLite session manager instances.

::: archipy.adapters.sqlite.sqlalchemy.session_manager_registry
options:
show_root_toc_entry: false
heading_level: 3

## Adapters

Concrete SQLite adapter built on the base SQLAlchemy adapter with SQLite-specific configuration.

::: archipy.adapters.sqlite.sqlalchemy.adapters
options:
show_root_toc_entry: false
heading_level: 3
