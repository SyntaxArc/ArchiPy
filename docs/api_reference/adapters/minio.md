# MinIO

The `minio` adapter provides integration with MinIO (and S3-compatible object storage) for uploading, downloading, and managing binary objects.

## ports

Abstract port interface defining the MinIO adapter contract for object storage operations.

::: archipy.adapters.minio.ports
    options:
      show_root_heading: true
      show_source: true

## adapters

Concrete MinIO adapter wrapping the MinIO Python SDK with ArchiPy conventions for object storage operations.

::: archipy.adapters.minio.adapters
    options:
      show_root_heading: true
      show_source: true
