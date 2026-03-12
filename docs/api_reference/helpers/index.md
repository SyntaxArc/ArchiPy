---
title: Helpers Overview
description: Overview of ArchiPy helper utilities including decorators, interceptors, metaclasses, and utils.
---

# Helpers

The `helpers` module provides pure utility functions, decorators, interceptors, and metaclasses that support common
development patterns across the application. All helpers are free of direct external I/O and database calls.

## Submodules

| Submodule                       | Description                                                                 |
|---------------------------------|-----------------------------------------------------------------------------|
| [Decorators](decorators.md)     | Function and class decorators for retry, caching, timing, tracing, and more |
| [Interceptors](interceptors.md) | Cross-cutting concern handlers for FastAPI and gRPC                         |
| [Metaclasses](metaclasses.md)   | Python metaclass utilities                                                  |
| [Utils](utils.md)               | General-purpose utility classes for common operations                       |

## Source Code

📁 Location: `archipy/helpers/`

🔗 [Browse Source](https://github.com/SyntaxArc/ArchiPy/tree/master/archipy/helpers)

## API Stability

| Component    | Status    | Notes            |
|--------------|-----------|------------------|
| Decorators   | 🟢 Stable | Production-ready |
| Interceptors | 🟢 Stable | Production-ready |
| Metaclasses  | 🟢 Stable | Production-ready |
| Utils        | 🟢 Stable | Production-ready |
