---
title: MinIO
description: API reference for the MinIO adapter ports, adapters, and mocks.
---

# MinIO

The `minio` adapter provides integration with MinIO (and S3-compatible object storage) for uploading, downloading, and
managing binary objects.

## Ports

Abstract port interface defining the MinIO adapter contract for object storage operations.

::: archipy.adapters.minio.ports
options:
show_root_toc_entry: false
heading_level: 3

## Adapters

Concrete MinIO adapter wrapping the MinIO Python SDK with ArchiPy conventions for object storage operations.

::: archipy.adapters.minio.adapters
options:
show_root_toc_entry: false
heading_level: 3
