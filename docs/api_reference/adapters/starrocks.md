---
title: StarRocks
description: API reference for the StarRocks adapter session managers and adapters.
---

# StarRocks

The `starrocks/sqlalchemy` adapter provides integration with StarRocks, a high-performance analytical database
compatible with the MySQL protocol, using SQLAlchemy.

## Session Managers

StarRocks-specific session manager handling connection management for the StarRocks analytical engine.

::: archipy.adapters.starrocks.sqlalchemy.session_managers
options:
show_root_toc_entry: false
heading_level: 3

## Session Manager Registry

Registry for StarRocks session manager instances.

::: archipy.adapters.starrocks.sqlalchemy.session_manager_registry
options:
show_root_toc_entry: false
heading_level: 3

## Adapters

Concrete StarRocks adapter built on the base SQLAlchemy adapter with StarRocks-specific dialect configuration.

::: archipy.adapters.starrocks.sqlalchemy.adapters
options:
show_root_toc_entry: false
heading_level: 3
