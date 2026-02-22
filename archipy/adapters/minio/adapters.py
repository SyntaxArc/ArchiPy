import logging
from collections.abc import Callable
from typing import Any, NoReturn, TypeVar, override

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, ConnectionError as BotocoreConnectionError, EndpointConnectionError

from archipy.adapters.minio.ports import MinioBucketType, MinioObjectType, MinioPolicyType, MinioPort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import MinioConfig
from archipy.helpers.decorators import ttl_cache_decorator
from archipy.models.errors import (
    AlreadyExistsError,
    ConfigurationError,
    ConnectionTimeoutError,
    InternalError,
    InvalidArgumentError,
    NetworkError,
    NotFoundError,
    PermissionDeniedError,
    ResourceExhaustedError,
    ServiceUnavailableError,
    StorageError,
)

# Type variables for decorators
T = TypeVar("T")  # Return type
F = TypeVar("F", bound=Callable[..., Any])  # Function type

logger = logging.getLogger(__name__)


class MinioExceptionHandlerMixin:
    """Mixin class to handle boto3 S3 exceptions in a consistent way."""

    @classmethod
    def _handle_client_exception(cls, exception: ClientError, operation: str) -> NoReturn:
        """Handle ClientError exceptions and map them to appropriate application errors.

        Args:
            exception: The original ClientError exception from boto3
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception error code
        """
        error_code = exception.response.get("Error", {}).get("Code", "")

        # Bucket existence errors
        if error_code in ("NoSuchBucket", "404"):
            raise NotFoundError(resource_type="bucket") from exception

        # Object existence errors
        if error_code in ("NoSuchKey", "NoSuchObject"):
            raise NotFoundError(resource_type="object") from exception

        # Bucket ownership/existence errors
        if error_code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise AlreadyExistsError(resource_type="bucket") from exception

        # Permission errors
        if error_code in ("AccessDenied", "Forbidden", "403"):
            raise PermissionDeniedError(
                additional_data={"details": f"Permission denied for operation: {operation}"},
            ) from exception

        # Resource limit errors
        if error_code in ("QuotaExceeded", "LimitExceeded", "TooManyBuckets"):
            raise ResourceExhaustedError(resource_type="storage") from exception

        # Invalid parameter errors
        if error_code in ("InvalidArgument", "InvalidParameterValue", "InvalidRequest"):
            raise InvalidArgumentError(argument_name=operation) from exception

        # Default: general storage error
        raise StorageError(additional_data={"operation": operation, "error_code": error_code}) from exception

    @classmethod
    def _handle_connection_exception(cls, exception: Exception, _operation: str) -> NoReturn:
        """Handle connection-related exceptions.

        Args:
            exception: The original exception
            operation: The operation that failed

        Raises:
            ConnectionTimeoutError or NetworkError or ServiceUnavailableError
        """
        error_msg = str(exception).lower()

        if "timeout" in error_msg or "timed out" in error_msg:
            raise ConnectionTimeoutError(service="S3") from exception

        if isinstance(exception, (BotocoreConnectionError, EndpointConnectionError)):
            raise NetworkError(service="S3") from exception

        if "unavailable" in error_msg or "connection" in error_msg:
            raise ServiceUnavailableError(service="S3") from exception

        raise NetworkError(service="S3") from exception

    @classmethod
    def _handle_general_exception(cls, exception: Exception, component: str) -> NoReturn:
        """Handle general exceptions by converting them to appropriate application errors.

        Args:
            exception: The original exception
            component: The component/operation name for context

        Raises:
            InternalError: A wrapped version of the original exception
        """
        raise InternalError(additional_data={"component": component}) from exception


class MinioAdapter(MinioPort, MinioExceptionHandlerMixin):
    """Concrete implementation of the MinioPort interface using boto3."""

    def __init__(self, minio_configs: MinioConfig | None = None) -> None:
        """Initialize MinioAdapter with configuration.

        Args:
            minio_configs: Optional MinIO/S3 configuration. If None, global config is used.

        Raises:
            ConfigurationError: If there is an error in the configuration.
            InvalidArgumentError: If required parameters are missing.
            NetworkError: If there are network errors connecting to S3/MinIO server.
        """
        try:
            # Determine config source (explicit or from global config)
            if minio_configs is not None:
                self.configs = minio_configs
            else:
                # First get global config, then extract MINIO config
                global_config = BaseConfig.global_config()
                if not hasattr(global_config, "MINIO"):
                    raise InvalidArgumentError(argument_name="MINIO")
                minio_config = getattr(global_config, "MINIO", None)
                if not isinstance(minio_config, MinioConfig):
                    raise InvalidArgumentError(argument_name="MINIO")
                self.configs = minio_config

            # Ensure we have a valid endpoint value
            endpoint = str(self.configs.ENDPOINT or "")
            if not endpoint:
                raise InvalidArgumentError(argument_name="endpoint")

            # Determine SSL usage (USE_SSL overrides SECURE if set)
            use_ssl = self.configs.USE_SSL if self.configs.USE_SSL is not None else self.configs.SECURE

            # Construct endpoint URL with protocol
            protocol = "https" if use_ssl else "http"
            endpoint_url = f"{protocol}://{endpoint}"

            # Configure boto3 client with retry and timeout settings
            boto_config = Config(
                signature_version=self.configs.SIGNATURE_VERSION,
                s3={
                    "addressing_style": self.configs.ADDRESSING_STYLE,
                },
                retries={
                    "max_attempts": self.configs.RETRIES_MAX_ATTEMPTS,
                    "mode": self.configs.RETRIES_MODE,
                },
                connect_timeout=self.configs.CONNECT_TIMEOUT,
                read_timeout=self.configs.READ_TIMEOUT,
                max_pool_connections=self.configs.MAX_POOL_CONNECTIONS,
            )

            # Create boto3 S3 client
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.configs.ACCESS_KEY,
                aws_secret_access_key=self.configs.SECRET_KEY,
                aws_session_token=self.configs.SESSION_TOKEN,
                region_name=self.configs.REGION,
                config=boto_config,
                verify=self.configs.VERIFY_SSL,
            )
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if "configuration" in error_code.lower():
                raise ConfigurationError(operation="s3") from e
            else:
                raise InternalError(additional_data={"component": "S3"}) from e
        except (BotocoreConnectionError, EndpointConnectionError) as e:
            raise NetworkError(service="S3") from e
        except Exception as e:
            raise InternalError(additional_data={"component": "S3"}) from e

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "clear_cache"):
                attr.clear_cache()

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists.

        Args:
            bucket_name: Name of the bucket to check.

        Returns:
            bool: True if bucket exists, False otherwise.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")
            self._client.head_bucket(Bucket=bucket_name)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchBucket", "404"):
                return False
            self._handle_client_exception(e, "bucket_exists")
            raise
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "bucket_exists")
            raise
        except Exception as e:
            self._handle_general_exception(e, "bucket_exists")
            raise
        else:
            return True

    @override
    def make_bucket(self, bucket_name: str) -> None:
        """Create a new bucket.

        Args:
            bucket_name: Name of the bucket to create.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            AlreadyExistsError: If the bucket already exists.
            PermissionDeniedError: If permission to create bucket is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")

            # Handle region-specific bucket creation
            create_bucket_config = {}
            if self.configs.REGION and self.configs.REGION != "us-east-1":
                create_bucket_config = {"CreateBucketConfiguration": {"LocationConstraint": self.configs.REGION}}

            if create_bucket_config:
                self._client.create_bucket(Bucket=bucket_name, **create_bucket_config)
            else:
                self._client.create_bucket(Bucket=bucket_name)

            self.clear_all_caches()
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "make_bucket")
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "make_bucket")
        except Exception as e:
            self._handle_general_exception(e, "make_bucket")

    @override
    def remove_bucket(self, bucket_name: str) -> None:
        """Remove a bucket.

        Args:
            bucket_name: Name of the bucket to remove.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to delete bucket is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")
            self._client.delete_bucket(Bucket=bucket_name)
            self.clear_all_caches()
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "remove_bucket")
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "remove_bucket")
        except Exception as e:
            self._handle_general_exception(e, "remove_bucket")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=1)
    def list_buckets(self) -> list[MinioBucketType]:
        """List all buckets.

        Returns:
            list: List of buckets and their creation dates.

        Raises:
            PermissionDeniedError: If permission to list buckets is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            response = self._client.list_buckets()
        except ClientError as e:
            self._handle_client_exception(e, "list_buckets")
            raise
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "list_buckets")
            raise
        except Exception as e:
            self._handle_general_exception(e, "list_buckets")
            raise
        else:
            # Convert buckets to MinioBucketType format
            buckets = response.get("Buckets", [])
            bucket_list: list[MinioBucketType] = [
                {"name": b["Name"], "creation_date": b["CreationDate"]} for b in buckets
            ]
            return bucket_list

    @override
    def put_object(self, bucket_name: str, object_name: str, file_path: str) -> None:
        """Upload a file to a bucket.

        Args:
            bucket_name: Destination bucket name.
            object_name: Object name in the bucket.
            file_path: Local file path to upload.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to upload is denied.
            ResourceExhaustedError: If storage limits are exceeded.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name or not object_name or not file_path:
                raise InvalidArgumentError(
                    argument_name=(
                        "bucket_name, object_name or file_path"
                        if not all([bucket_name, object_name, file_path])
                        else "bucket_name"
                        if not bucket_name
                        else "object_name"
                        if not object_name
                        else "file_path"
                    ),
                )
            self._client.upload_file(file_path, bucket_name, object_name)
            if hasattr(self.list_objects, "clear_cache"):
                self.list_objects.clear_cache()
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "put_object")
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "put_object")
        except Exception as e:
            self._handle_general_exception(e, "put_object")

    @override
    def get_object(self, bucket_name: str, object_name: str, file_path: str) -> None:
        """Download an object to a file.

        Args:
            bucket_name: Source bucket name.
            object_name: Object name in the bucket.
            file_path: Local file path to save the object.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket or object does not exist.
            PermissionDeniedError: If permission to download is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name or not object_name or not file_path:
                raise InvalidArgumentError(
                    argument_name=(
                        "bucket_name, object_name or file_path"
                        if not all([bucket_name, object_name, file_path])
                        else "bucket_name"
                        if not bucket_name
                        else "object_name"
                        if not object_name
                        else "file_path"
                    ),
                )
            self._client.download_file(bucket_name, object_name, file_path)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "get_object")
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "get_object")
        except Exception as e:
            self._handle_general_exception(e, "get_object")

    @override
    def remove_object(self, bucket_name: str, object_name: str) -> None:
        """Remove an object from a bucket.

        Args:
            bucket_name: Bucket name.
            object_name: Object name to remove.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket or object does not exist.
            PermissionDeniedError: If permission to remove is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name or not object_name:
                raise InvalidArgumentError(
                    argument_name=(
                        "bucket_name or object_name"
                        if not all([bucket_name, object_name])
                        else "bucket_name"
                        if not bucket_name
                        else "object_name"
                    ),
                )
            self._client.delete_object(Bucket=bucket_name, Key=object_name)
            if hasattr(self.list_objects, "clear_cache"):
                self.list_objects.clear_cache()
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "remove_object")
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "remove_object")
        except Exception as e:
            self._handle_general_exception(e, "remove_object")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        *,
        recursive: bool = False,
    ) -> list[MinioObjectType]:
        """List objects in a bucket.

        Args:
            bucket_name: Bucket name.
            prefix: Optional prefix to filter objects.
            recursive: Whether to list objects recursively.

        Returns:
            list: List of objects with metadata.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to list objects is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")

            # Build list_objects_v2 parameters
            params = {"Bucket": bucket_name}
            if prefix:
                params["Prefix"] = prefix
            if not recursive:
                params["Delimiter"] = "/"

            # Handle pagination
            object_list: list[MinioObjectType] = []
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(**params):
                object_list.extend(
                    {
                        "object_name": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                    for obj in page.get("Contents", [])
                )
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "list_objects")
            raise
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "list_objects")
            raise
        except Exception as e:
            self._handle_general_exception(e, "list_objects")
            raise
        else:
            return object_list

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def stat_object(self, bucket_name: str, object_name: str) -> MinioObjectType:
        """Get object metadata.

        Args:
            bucket_name: Bucket name.
            object_name: Object name to get stats for.

        Returns:
            dict: Object metadata including name, size, last modified date, etc.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket or object does not exist.
            PermissionDeniedError: If permission to get stats is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name or not object_name:
                raise InvalidArgumentError(
                    argument_name=(
                        "bucket_name or object_name"
                        if not all([bucket_name, object_name])
                        else "bucket_name"
                        if not bucket_name
                        else "object_name"
                    ),
                )
            response = self._client.head_object(Bucket=bucket_name, Key=object_name)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "stat_object")
            raise
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "stat_object")
            raise
        except Exception as e:
            self._handle_general_exception(e, "stat_object")
            raise
        else:
            # Convert response to MinioObjectType format
            return {
                "object_name": object_name,
                "size": response.get("ContentLength", 0),
                "last_modified": response.get("LastModified"),
                "content_type": response.get("ContentType"),
                "etag": response.get("ETag", "").strip('"'),
            }

    @override
    def presigned_get_object(self, bucket_name: str, object_name: str, expires: int = 3600) -> str:
        """Generate a presigned URL for downloading an object.

        Args:
            bucket_name: Bucket name.
            object_name: Object name to generate URL for.
            expires: URL expiry time in seconds.

        Returns:
            str: Presigned URL for downloading the object.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket or object does not exist.
            PermissionDeniedError: If permission to generate URL is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name or not object_name:
                raise InvalidArgumentError(
                    argument_name=(
                        "bucket_name or object_name"
                        if not all([bucket_name, object_name])
                        else "bucket_name"
                        if not bucket_name
                        else "object_name"
                    ),
                )
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=expires,
            )
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "presigned_get_object")
            raise
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "presigned_get_object")
            raise
        except Exception as e:
            self._handle_general_exception(e, "presigned_get_object")
            raise
        else:
            typed_url: str = url
            return typed_url

    @override
    def presigned_put_object(self, bucket_name: str, object_name: str, expires: int = 3600) -> str:
        """Generate a presigned URL for uploading an object.

        Args:
            bucket_name: Bucket name.
            object_name: Object name to generate URL for.
            expires: URL expiry time in seconds.

        Returns:
            str: Presigned URL for uploading the object.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to generate URL is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name or not object_name:
                raise InvalidArgumentError(
                    argument_name=(
                        "bucket_name or object_name"
                        if not all([bucket_name, object_name])
                        else "bucket_name"
                        if not bucket_name
                        else "object_name"
                    ),
                )
            url = self._client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=expires,
            )
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "presigned_put_object")
            raise
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "presigned_put_object")
            raise
        except Exception as e:
            self._handle_general_exception(e, "presigned_put_object")
            raise
        else:
            typed_url: str = url
            return typed_url

    @override
    def set_bucket_policy(self, bucket_name: str, policy: str) -> None:
        """Set bucket policy.

        Args:
            bucket_name: Bucket name.
            policy: JSON policy string.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to set policy is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name or not policy:
                raise InvalidArgumentError(
                    argument_name=(
                        "bucket_name or policy"
                        if not all([bucket_name, policy])
                        else "bucket_name"
                        if not bucket_name
                        else "policy"
                    ),
                )
            self._client.put_bucket_policy(Bucket=bucket_name, Policy=policy)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "set_bucket_policy")
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "set_bucket_policy")
        except Exception as e:
            self._handle_general_exception(e, "set_bucket_policy")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)
    def get_bucket_policy(self, bucket_name: str) -> MinioPolicyType:
        """Get bucket policy.

        Args:
            bucket_name: Bucket name.

        Returns:
            dict: Bucket policy information.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to get policy is denied.
            ServiceUnavailableError: If the S3 service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")
            response = self._client.get_bucket_policy(Bucket=bucket_name)
            policy = response.get("Policy", "{}")
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except ClientError as e:
            self._handle_client_exception(e, "get_bucket_policy")
            raise
        except (ConnectionError, EndpointConnectionError) as e:
            self._handle_connection_exception(e, "get_bucket_policy")
            raise
        except Exception as e:
            self._handle_general_exception(e, "get_bucket_policy")
            raise
        else:
            # Convert policy to MinioPolicyType format
            policy_dict: MinioPolicyType = {"policy": policy}
            return policy_dict
