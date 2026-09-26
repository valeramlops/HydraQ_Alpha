"""S3-compatible object storage client built on MinIO SDK.

Implements the Zero-RAM upload pattern via presigned URLs,
delegating large file transfers directly between the client and MinIO
without buffering through the application server's memory.
"""

import io
import logging
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from libs.storage.config import StorageConfig

logger = logging.getLogger(__name__)


class S3StorageClient:
    """MinIO S3 storage client with Zero-RAM presigned URL support.

    Provides bucket management, presigned URL generation for direct
    client-to-S3 uploads/downloads, and utility methods for small
    payloads (metadata, checkpoints).

    Attributes:
        config: Storage configuration instance.
        client: Underlying ``minio.Minio`` SDK client.
    """

    def __init__(self, config: StorageConfig | None = None) -> None:
        """Initialize the S3 storage client.

        Args:
            config: Optional storage configuration. Uses default
                ``StorageConfig()`` when not provided.
        """
        self.config = config or StorageConfig()
        self.client = Minio(
            endpoint=self.config.endpoint,
            access_key=self.config.access_key,
            secret_key=self.config.secret_key,
            secure=self.config.secure,
        )

    def ensure_buckets_exist(self) -> None:
        """Create default buckets if they do not already exist.

        Iterates over ``config.default_buckets`` and creates each
        bucket that is not yet present in the MinIO instance.

        Raises:
            S3Error: If a MinIO API call fails for reasons other
                than the bucket already existing.
        """
        for bucket_name in self.config.default_buckets:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info("Created bucket '%s'", bucket_name)
            else:
                logger.debug("Bucket '%s' already exists", bucket_name)

    def generate_presigned_upload_url(
        self,
        bucket: str,
        object_name: str,
        expires_seconds: int = 3600,
    ) -> str:
        """Generate a presigned PUT URL for direct client upload.

        Enables the Zero-RAM pattern: the API gateway returns this
        URL to the client, which uploads directly to MinIO without
        proxying data through application memory.

        Args:
            bucket: Target bucket name.
            object_name: Object key within the bucket.
            expires_seconds: URL validity duration in seconds.

        Returns:
            Presigned PUT URL string.
        """
        return self.client.presigned_put_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(seconds=expires_seconds),
        )

    def generate_presigned_download_url(
        self,
        bucket: str,
        object_name: str,
        expires_seconds: int = 3600,
    ) -> str:
        """Generate a presigned GET URL for direct client download.

        Args:
            bucket: Source bucket name.
            object_name: Object key within the bucket.
            expires_seconds: URL validity duration in seconds.

        Returns:
            Presigned GET URL string.
        """
        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(seconds=expires_seconds),
        )

    def check_health(self) -> bool:
        """Verify MinIO connectivity by listing buckets.

        Returns:
            ``True`` if MinIO responds successfully, ``False`` on
            any network or S3 error.
        """
        try:
            self.client.list_buckets()
        except (S3Error, Exception):
            logger.exception("MinIO health check failed")
            return False
        return True

    def upload_bytes(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload raw bytes directly into a bucket.

        Intended for small payloads such as model metadata or
        serialized configuration. For large files, prefer the
        presigned URL pattern via ``generate_presigned_upload_url``.

        Args:
            bucket: Target bucket name.
            object_name: Object key within the bucket.
            data: Raw bytes to store.
            content_type: MIME type of the stored object.
        """
        stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=stream,
            length=len(data),
            content_type=content_type,
        )

    def download_bytes(self, bucket: str, object_name: str) -> bytes:
        """Download an object and return its content as raw bytes.

        Args:
            bucket: Source bucket name.
            object_name: Object key within the bucket.

        Returns:
            Raw bytes of the stored object.
        """
        response = self.client.get_object(
            bucket_name=bucket,
            object_name=object_name,
        )
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
