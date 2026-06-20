"""MinIO port definitions for ArchiPy."""

from abc import abstractmethod
from typing import Any, BinaryIO

# Define type aliases for better type hinting
MinioObjectType = dict[str, Any]
MinioBucketType = dict[str, Any]
MinioPolicyType = dict[str, Any]
MinioLifecycleRuleType = dict[str, Any]


class MinioPort:
    """Interface for MinIO operations providing a standardized access pattern.

    This interface defines the contract for MinIO adapters, ensuring consistent
    implementation of object storage operations across different adapters.
    """

    # Bucket Operations
    @abstractmethod
    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if a bucket exists."""
        raise NotImplementedError

    @abstractmethod
    def make_bucket(self, bucket_name: str) -> None:
        """Create a new bucket."""
        raise NotImplementedError

    @abstractmethod
    def remove_bucket(self, bucket_name: str) -> None:
        """Remove a bucket."""
        raise NotImplementedError

    @abstractmethod
    def list_buckets(self) -> list[MinioBucketType]:
        """List all buckets."""
        raise NotImplementedError

    # Object Operations
    @abstractmethod
    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Upload a file to a bucket.

        Args:
            bucket_name: Destination bucket name.
            object_name: Object name in the bucket.
            file_path: Local file path to upload.
            tags: Optional key-value tags to attach to the object. Tags can be used
                with bucket lifecycle rules to implement per-object TTL expiration.
        """
        raise NotImplementedError

    @abstractmethod
    def get_object(self, bucket_name: str, object_name: str, file_path: str) -> None:
        """Download an object to a file."""
        raise NotImplementedError

    @abstractmethod
    def remove_object(self, bucket_name: str, object_name: str) -> None:
        """Remove an object from a bucket."""
        raise NotImplementedError

    @abstractmethod
    def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        *,  # Force recursive to be keyword-only to avoid boolean flag issues
        recursive: bool = False,
    ) -> list[MinioObjectType]:
        """List objects in a bucket.

        Args:
            bucket_name: The name of the bucket to list objects from
            prefix: Optional prefix to filter objects by
            recursive: Whether to list objects recursively (include sub-directories)

        Returns:
            A list of MinioObjectType objects
        """
        raise NotImplementedError

    @abstractmethod
    def stat_object(self, bucket_name: str, object_name: str) -> MinioObjectType:
        """Get object metadata."""
        raise NotImplementedError

    # Presigned URL Operations
    @abstractmethod
    def presigned_get_object(self, bucket_name: str, object_name: str, expires: int = 3600) -> str:
        """Generate a presigned URL for downloading an object."""
        raise NotImplementedError

    @abstractmethod
    def presigned_put_object(self, bucket_name: str, object_name: str, expires: int = 3600) -> str:
        """Generate a presigned URL for uploading an object."""
        raise NotImplementedError

    # Policy Operations
    @abstractmethod
    def set_bucket_policy(self, bucket_name: str, policy: str) -> None:
        """Set bucket policy."""
        raise NotImplementedError

    @abstractmethod
    def get_bucket_policy(self, bucket_name: str) -> MinioPolicyType:
        """Get bucket policy."""
        raise NotImplementedError

    @abstractmethod
    def copy_object(
        self,
        src_bucket_name: str,
        src_object_name: str,
        dest_bucket_name: str,
        dest_object_name: str,
    ) -> None:
        """Copy an object within or between buckets."""
        raise NotImplementedError

    @abstractmethod
    def put_object_stream(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes | BinaryIO,
        length: int = -1,
        content_type: str = "application/octet-stream",
        tags: dict[str, str] | None = None,
    ) -> None:
        """Upload data from a bytes buffer or binary stream to a bucket.

        Unlike put_object which requires a local file path, this method accepts
        in-memory bytes or any binary stream, avoiding the need for a temporary file.

        Args:
            bucket_name: Destination bucket name.
            object_name: Object name in the bucket.
            data: Content to upload as raw bytes or a binary stream (BinaryIO).
            length: Content length in bytes. If -1, computed automatically for bytes;
                for streams, providing the exact length avoids buffering overhead.
            content_type: MIME type of the content. Defaults to "application/octet-stream".
            tags: Optional key-value tags to attach to the object. Tags can be used
                with bucket lifecycle rules to implement per-object TTL expiration.
        """
        raise NotImplementedError

    @abstractmethod
    def get_object_stream(self, bucket_name: str, object_name: str) -> bytes:
        """Download an object and return its content as bytes.

        Unlike get_object which requires a local file path, this method returns
        the object content directly in memory, avoiding a temporary file.

        Args:
            bucket_name: Source bucket name.
            object_name: Object name in the bucket.

        Returns:
            bytes: The full content of the object.
        """
        raise NotImplementedError

    # Object Tag Operations
    @abstractmethod
    def set_object_tags(self, bucket_name: str, object_name: str, tags: dict[str, str]) -> None:
        """Set tags on an existing object, replacing any existing tags.

        Tags are key-value pairs that can be used with bucket lifecycle rules to
        implement TTL-based expiration. For example, tag an object with
        ``{"ttl-days": "7"}`` and create a matching lifecycle rule to auto-delete
        it after 7 days.

        Args:
            bucket_name: Bucket containing the object.
            object_name: Object name to tag.
            tags: Key-value mapping of tag names to values.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket or object does not exist.
            PermissionDeniedError: If permission to set tags is denied.
            StorageError: If there's a storage-related error.
        """
        raise NotImplementedError

    @abstractmethod
    def get_object_tags(self, bucket_name: str, object_name: str) -> dict[str, str]:
        """Return the tags attached to an object.

        Args:
            bucket_name: Bucket containing the object.
            object_name: Object name whose tags to retrieve.

        Returns:
            dict[str, str]: Mapping of tag key to tag value. Empty dict if no tags.

        Raises:
            InvalidArgumentError: If any required parameter is empty.
            NotFoundError: If the bucket or object does not exist.
            PermissionDeniedError: If permission to get tags is denied.
            StorageError: If there's a storage-related error.
        """
        raise NotImplementedError

    # Lifecycle / TTL Operations
    @abstractmethod
    def set_bucket_lifecycle(self, bucket_name: str, rules: list[MinioLifecycleRuleType]) -> None:
        """Set the lifecycle configuration for a bucket.

        Lifecycle rules control automatic expiration (TTL) of objects. Each rule is a
        dict that maps to the S3 ``LifecycleRule`` structure. A minimal expiration rule::

            {
                "ID": "expire-after-7-days",
                "Status": "Enabled",
                "Filter": {"Prefix": "uploads/"},
                "Expiration": {"Days": 7},
            }

        To expire only objects with a specific tag::

            {
                "ID": "expire-tagged-7days",
                "Status": "Enabled",
                "Filter": {"Tag": {"Key": "ttl-days", "Value": "7"}},
                "Expiration": {"Days": 7},
            }

        Args:
            bucket_name: Target bucket name.
            rules: List of lifecycle rule dicts (S3 ``LifecycleRule`` format).

        Raises:
            InvalidArgumentError: If bucket_name is empty or rules is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to set lifecycle is denied.
            StorageError: If there's a storage-related error.
        """
        raise NotImplementedError

    @abstractmethod
    def get_bucket_lifecycle(self, bucket_name: str) -> list[MinioLifecycleRuleType]:
        """Return the lifecycle rules configured for a bucket.

        Args:
            bucket_name: Bucket name.

        Returns:
            list[MinioLifecycleRuleType]: List of lifecycle rule dicts, or an empty
                list if no lifecycle configuration is set.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to get lifecycle is denied.
            StorageError: If there's a storage-related error.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_bucket_lifecycle(self, bucket_name: str) -> None:
        """Delete the lifecycle configuration from a bucket.

        After this call the bucket has no lifecycle rules and objects will not be
        automatically expired.

        Args:
            bucket_name: Bucket name.

        Raises:
            InvalidArgumentError: If bucket_name is empty.
            NotFoundError: If the bucket does not exist.
            PermissionDeniedError: If permission to delete lifecycle is denied.
            StorageError: If there's a storage-related error.
        """
        raise NotImplementedError
