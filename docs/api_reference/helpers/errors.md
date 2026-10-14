---
title: Errors
description: API reference for ArchiPy error handling helpers shared by FastAPI and gRPC.
---

# Errors

The `helpers/errors` subpackage turns exceptions into transport responses. `capture`, `validation` and `mapping` are
transport-agnostic; `fastapi` and `grpc` need the matching extra.

## Capture

::: archipy.helpers.errors.capture
    options:
      show_root_toc_entry: false
      heading_level: 3

## Validation

::: archipy.helpers.errors.validation
    options:
      show_root_toc_entry: false
      heading_level: 3

## Mapping

::: archipy.helpers.errors.mapping
    options:
      show_root_toc_entry: false
      heading_level: 3

## FastAPI

::: archipy.helpers.errors.fastapi.handlers
    options:
      show_root_toc_entry: false
      heading_level: 3

::: archipy.helpers.errors.fastapi.openapi
    options:
      show_root_toc_entry: false
      heading_level: 3

::: archipy.helpers.errors.fastapi.response_dtos
    options:
      show_root_toc_entry: false
      heading_level: 3

## gRPC

::: archipy.helpers.errors.grpc.abort
    options:
      show_root_toc_entry: false
      heading_level: 3

::: archipy.helpers.errors.grpc.interceptors
    options:
      show_root_toc_entry: false
      heading_level: 3
