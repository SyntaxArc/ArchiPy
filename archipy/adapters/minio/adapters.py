import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any, TypeVar, override

from minio import Minio
from minio.error import S3Error

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
    """Mixin class to handle MinIO/S3 exceptions in a consistent way."""

    @classmethod
    def _handle_s3_exception(cls, exception: S3Error, operation: str) -> None:
        """Handle S3Error exceptions and map them to appropriate application errors.

        Args:
            exception: The original S3Error exception
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception type/content
        """
        error_msg = str(exception).lower()

        # Bucket existence errors
        if "NoSuchBucket" in str(exception):
            raise NotFoundError(resource_type="bucket") from exception

        # Object existence errors
        if "NoSuchKey" in str(exception):
            raise NotFoundError(resource_type="object") from exception

        # Bucket ownership/existence errors
        if "BucketAlreadyOwnedByYou" in str(exception) or "BucketAlreadyExists" in str(exception):
            raise AlreadyExistsError(resource_type="bucket") from exception

        # Permission errors
        if "AccessDenied" in str(exception):
            raise PermissionDeniedError(
                additional_data={"details": f"Permission denied for operation: {operation}"},
            ) from exception

        # Resource limit errors
        if "quota" in error_msg or "limit" in error_msg or "exceeded" in error_msg:
            raise ResourceExhaustedError(resource_type="storage") from exception

        # Connection/availability errors
        if "timeout" in error_msg:
            raise ConnectionTimeoutError(service="MinIO") from exception

        if "unavailable" in error_msg or "connection" in error_msg:
            raise ServiceUnavailableError(service="MinIO") from exception

        # Default: general storage error
        raise StorageError(additional_data={"operation": operation}) from exception

    @classmethod
    def _handle_general_exception(cls, exception: Exception, component: str) -> None:
        """Handle general exceptions by converting them to appropriate application errors.

        Args:
            exception: The original exception
            component: The component/operation name for context

        Raises:
            InternalError: A wrapped version of the original exception
        """
        raise InternalError(additional_data={"component": component}) from exception


class MinioAdapter(MinioPort, MinioExceptionHandlerMixin):
    """Concrete implementation of the MinioPort interface using the minio library."""

    def __init__(self, minio_configs: MinioConfig | None = None) -> None:
        """Initialize MinioAdapter with configuration.

        Args:
            minio_configs: Optional MinIO configuration. If None, global config is used.

        Raises:
            ConfigurationError: If there is an error in the MinIO configuration.
            InvalidArgumentError: If required parameters are missing.
            NetworkError: If there are network errors connecting to MinIO server.
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

            self._adapter = Minio(
                endpoint,
                access_key=self.configs.ACCESS_KEY,
                secret_key=self.configs.SECRET_KEY,
                session_token=self.configs.SESSION_TOKEN,
                secure=self.configs.SECURE,
                region=self.configs.REGION,
            )
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            error_msg = str(e).lower()
            if "configuration" in error_msg:
                raise ConfigurationError(operation="minio") from e
            elif "connection" in error_msg:
                raise NetworkError(service="MinIO") from e
            else:
                raise InternalError(additional_data={"component": "MinIO"}) from e
        except Exception as e:
            raise InternalError(additional_data={"component": "MinIO"}) from e

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "clear_cache"):
                attr.clear_cache()

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists.

        Args:
            bucket_name: Name of the bucket to check.

        Returns:
            bool: True if bucket exists, False otherwise.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            ServiceUnavailableError: If the MinIO service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")
            result = self._adapter.bucket_exists(bucket_name)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            if "NoSuchBucket" in str(e):
                return False
            self._handle_s3_exception(e, "bucket_exists")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        except Exception as e:
            self._handle_general_exception(e, "bucket_exists")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # result is bool from minio client, compatible with return type
            typed_result: bool = result
            return typed_result

    @override
    def make_bucket(self, bucket_name: str) -> None:
        """Create a new bucket.

        Args:
            bucket_name: Name of the bucket to create.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            AlreadyExistsError: If the bucket already exists.
            PermissionDeniedError: If permission to create bucket is denied.
            ServiceUnavailableError: If the MinIO service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")
            self._adapter.make_bucket(bucket_name)
            self.clear_all_caches()  # Clear cache since bucket list changed
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "make_bucket")
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
            ServiceUnavailableError: If the MinIO service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")
            self._adapter.remove_bucket(bucket_name)
            self.clear_all_caches()  # Clear cache since bucket list changed
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "remove_bucket")
        except Exception as e:
            self._handle_general_exception(e, "remove_bucket")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=1)  # Cache for 5 minutes
    def list_buckets(self) -> list[MinioBucketType]:
        """List all buckets.

        Returns:
            list: List of buckets and their creation dates.

        Raises:
            PermissionDeniedError: If permission to list buckets is denied.
            ServiceUnavailableError: If the MinIO service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            buckets = self._adapter.list_buckets()
        except S3Error as e:
            self._handle_s3_exception(e, "list_buckets")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        except Exception as e:
            self._handle_general_exception(e, "list_buckets")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # Convert buckets to MinioBucketType format
            bucket_list: list[MinioBucketType] = [{"name": b.name, "creation_date": b.creation_date} for b in buckets]
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
            ServiceUnavailableError: If the MinIO service is unavailable.
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
            self._adapter.fput_object(bucket_name, object_name, file_path)
            if hasattr(self.list_objects, "clear_cache"):
                self.list_objects.clear_cache()  # Clear object list cache
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "put_object")
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
            ServiceUnavailableError: If the MinIO service is unavailable.
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
            self._adapter.fget_object(bucket_name, object_name, file_path)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "get_object")
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
            ServiceUnavailableError: If the MinIO service is unavailable.
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
            self._adapter.remove_object(bucket_name, object_name)
            if hasattr(self.list_objects, "clear_cache"):
                self.list_objects.clear_cache()  # Clear object list cache
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "remove_object")
        except Exception as e:
            self._handle_general_exception(e, "remove_object")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
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
            ServiceUnavailableError: If the MinIO service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")
            objects = self._adapter.list_objects(bucket_name, prefix=prefix, recursive=recursive)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "list_objects")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        except Exception as e:
            self._handle_general_exception(e, "list_objects")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # Convert objects to MinioObjectType format
            object_list: list[MinioObjectType] = [
                {"object_name": obj.object_name, "size": obj.size, "last_modified": obj.last_modified}
                for obj in objects
            ]
            return object_list

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
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
            ServiceUnavailableError: If the MinIO service is unavailable.
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
            obj = self._adapter.stat_object(bucket_name, object_name)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "stat_object")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        except Exception as e:
            self._handle_general_exception(e, "stat_object")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # Convert object to MinioObjectType format
            return {
                "object_name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified,
                "content_type": obj.content_type,
                "etag": obj.etag,
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
            ServiceUnavailableError: If the MinIO service is unavailable.
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
            url = self._adapter.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires),
            )
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "presigned_get_object")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        except Exception as e:
            self._handle_general_exception(e, "presigned_get_object")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # url is str from minio client, compatible with return type
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
            ServiceUnavailableError: If the MinIO service is unavailable.
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
            url = self._adapter.presigned_put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires),
            )
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "presigned_put_object")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        except Exception as e:
            self._handle_general_exception(e, "presigned_put_object")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # url is str from minio client, compatible with return type
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
            ServiceUnavailableError: If the MinIO service is unavailable.
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
            self._adapter.set_bucket_policy(bucket_name, policy)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "set_bucket_policy")
        except Exception as e:
            self._handle_general_exception(e, "set_bucket_policy")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
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
            ServiceUnavailableError: If the MinIO service is unavailable.
            StorageError: If there's a storage-related error.
        """
        try:
            if not bucket_name:
                raise InvalidArgumentError(argument_name="bucket_name")
            policy = self._adapter.get_bucket_policy(bucket_name)
        except InvalidArgumentError:
            # Pass through our custom errors
            raise
        except S3Error as e:
            self._handle_s3_exception(e, "get_bucket_policy")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        except Exception as e:
            self._handle_general_exception(e, "get_bucket_policy")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # Convert policy to MinioPolicyType format
            policy_dict: MinioPolicyType = {"policy": policy}
            return policy_dict
