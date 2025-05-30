# Minio Adapter

The Minio adapter provides a clean interface for interacting with MinIO and S3-compatible object storage services.

## Features

- Bucket operations (create, list, delete)
- Object operations (upload, download, delete)
- Presigned URL generation
- Bucket policy management
- Built-in caching for performance optimization
- Comprehensive error handling with domain-specific exceptions

## Basic Usage

### Configuration

Configure MinIO in your application's config:

```python
from archipy.configs.base_config import BaseConfig

# Method 1: Using environment variables
# MINIO__ENDPOINT=localhost:9000
# MINIO__ACCESS_KEY=minioadmin
# MINIO__SECRET_KEY=minioadmin

# Method 2: Direct configuration
BaseConfig.global_config().MINIO.ENDPOINT = "localhost:9000"
BaseConfig.global_config().MINIO.ACCESS_KEY = "minioadmin"
BaseConfig.global_config().MINIO.SECRET_KEY = "minioadmin"
BaseConfig.global_config().MINIO.SECURE = False  # Set to True for HTTPS
```

### Initializing the Adapter

```python
from archipy.adapters.minio.adapters import MinioAdapter

# Use global configuration
minio = MinioAdapter()

# Or provide specific configuration
from archipy.configs.config_template import MinioConfig

custom_config = MinioConfig(
    ENDPOINT="play.min.io:9000",
    ACCESS_KEY="your-access-key",
    SECRET_KEY="your-secret-key",
    SECURE=True
)
minio = MinioAdapter(custom_config)
```

### Bucket Operations

```python
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Check if bucket exists
if not minio.bucket_exists("my-bucket"):
    # Create bucket
    minio.make_bucket("my-bucket")
    logger.info("Bucket created successfully")

# List all buckets
buckets = minio.list_buckets()
for bucket in buckets:
    logger.info(f"Bucket: {bucket['name']}, Created: {bucket['creation_date']}")

# Remove bucket
minio.remove_bucket("my-bucket")
```

### Working with Objects

```python
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Upload a file
minio.put_object("my-bucket", "document.pdf", "/path/to/local/document.pdf")

# Download an object
minio.get_object("my-bucket", "document.pdf", "/path/to/download/document.pdf")

# List objects in a bucket
objects = minio.list_objects("my-bucket", prefix="documents/", recursive=True)
for obj in objects:
    logger.info(f"Object: {obj['object_name']}, Size: {obj['size']} bytes")

# Get object metadata
metadata = minio.stat_object("my-bucket", "document.pdf")
logger.info(f"Content type: {metadata['content_type']}")
logger.info(f"Last modified: {metadata['last_modified']}")

# Remove an object
minio.remove_object("my-bucket", "document.pdf")
```

### Generating Presigned URLs

```python
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Generate a presigned URL for downloading (valid for 1 hour by default)
download_url = minio.presigned_get_object("my-bucket", "document.pdf")
logger.info(f"Download URL: {download_url}")

# Generate a presigned URL for uploading (with custom expiry time in seconds)
upload_url = minio.presigned_put_object("my-bucket", "new-document.pdf", expires=7200)  # 2 hours
logger.info(f"Upload URL: {upload_url}")
```

### Managing Bucket Policies

```python
import logging
import json

# Configure logging
logger = logging.getLogger(__name__)

# Set a read-only policy for a bucket
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::my-bucket/*"]
        }
    ]
}
minio.set_bucket_policy("my-bucket", json.dumps(policy))

# Get bucket policy
policy_info = minio.get_bucket_policy("my-bucket")
logger.info(f"Bucket policy: {policy_info['policy']}")
```

## Error Handling

The MinioAdapter uses ArchiPy's domain-specific exceptions for consistent error handling:

```python
import logging
from archipy.models.errors import (
    AlreadyExistsError,
    InternalError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
)

# Configure logging
logger = logging.getLogger(__name__)

try:
    minio.make_bucket("existing-bucket")
except AlreadyExistsError:
    logger.warning("Bucket already exists")
except PermissionDeniedError:
    logger.exception("Permission denied to create bucket")
except InvalidArgumentError as e:
    logger.exception(f"Invalid argument: {e}")
except InternalError as e:
    logger.exception(f"Internal error: {e}")
```

## Performance Optimization

The MinioAdapter includes TTL caching for frequently accessed operations:

```python
# Check if bucket exists (cached for 5 minutes)
minio.bucket_exists("my-bucket")

# List buckets (cached for 5 minutes)
minio.list_buckets()

# Clear all caches if needed
minio.clear_all_caches()
```

## Integration with Web Applications

### FastAPI Example

```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse
import tempfile
import os

from archipy.adapters.minio.adapters import MinioAdapter
from archipy.models.errors import NotFoundError, PermissionDeniedError

app = FastAPI()
minio = MinioAdapter()

@app.post("/upload/{bucket_name}")
async def upload_file(bucket_name: str, file: UploadFile):
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            content = await file.read()
            temp.write(content)
            temp_path = temp.name

        # Upload to MinIO
        try:
            minio.put_object(bucket_name, file.filename, temp_path)
            return {"message": f"File {file.filename} uploaded successfully"}
        finally:
            os.unlink(temp_path)  # Clean up temp file
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{bucket_name}/{object_name}")
async def download_file(bucket_name: str, object_name: str):
    try:
        # Generate presigned URL
        url = minio.presigned_get_object(bucket_name, object_name, expires=3600)
        return RedirectResponse(url)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Testing with BDD

The Minio adapter comes with BDD tests to verify functionality. Here's a sample feature file:

```gherkin
Feature: MinIO Operations Testing
  As a developer
  I want to test MinIO storage operations
  So that I can ensure reliable object storage functionality

  Background:
    Given a configured MinIO adapter

  Scenario: Create and verify a bucket
    When I create a bucket named "test-bucket"
    Then the bucket "test-bucket" should exist
    And the bucket list should include "test-bucket"

  Scenario: Upload and retrieve object
    Given a bucket named "test-bucket" exists
    When I upload a file "test.txt" with content "Hello World" to bucket "test-bucket"
    Then the object "test.txt" should exist in bucket "test-bucket"
    And downloading "test.txt" from "test-bucket" should return content "Hello World"
```
