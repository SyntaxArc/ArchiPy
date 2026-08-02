---
title: MySQL
description: API reference for the MySQL adapter session managers and adapters.
---

# MySQL

The `mysql/sqlalchemy` adapter provides a MySQL-specific SQLAlchemy integration, including a concrete adapter,
session manager, and session manager registry that extend the base SQLAlchemy components.

## Session Managers

MySQL-specific session manager handling connection pooling and lifecycle for MySQL databases.

::: archipy.adapters.mysql.sqlalchemy.session_managers
options:
show_root_toc_entry: false
heading_level: 3

## Session Manager Registry

Registry for MySQL session manager instances.

::: archipy.adapters.mysql.sqlalchemy.session_manager_registry
options:
show_root_toc_entry: false
heading_level: 3

## Adapters

Concrete MySQL adapter built on top of the base SQLAlchemy adapter with MySQL-specific configuration.

::: archipy.adapters.mysql.sqlalchemy.adapters
options:
show_root_toc_entry: false
heading_level: 3
