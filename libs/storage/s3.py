"""S3-compatible object storage client built on MinIO SDK.

Implements the Zero-RAM upload pattern via presigned URLs and provides
both synchronous (for Celery workers) and asynchronous (for FastAPI event loop)
clients without blocking execution threads.
"""

import asyncio
import io
import logging
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from libs.storage.config import StorageConfig

logger = logging.getLogger(__name__)


class S3StorageClient:
    """Synchronous MinIO S3 storage client for worker processes and batch jobs.

    Attributes:
        config: Storage configuration instance.
        client: Underlying minio.Minio SDK client instance.
    """

    def __init__(self, config: StorageConfig | None = None) -> None:
        """Initialize the synchronous S3 storage client.

        Args:
            config: Optional configuration. Uses default StorageConfig when omitted.
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

        Raises:
            S3Error: If a MinIO API call fails unexpectedly.
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
        """Generate a presigned PUT URL for direct client upload (Zero-RAM pattern).

        Args:
            bucket: Target bucket name.
            object_name: Object key within the bucket.
            expires_seconds: URL validity duration in seconds (default: 3600).

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
            expires_seconds: URL validity duration in seconds (default: 3600).

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
            True if MinIO responds successfully, False on any network or S3 error.
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


class AsyncS3StorageClient:
    """Asynchronous wrapper for MinIO client for non-blocking FastAPI integration.

    Delegates blocking socket I/O operations of the synchronous MinIO SDK
    to Python's default thread pool executor via ``asyncio.to_thread``.
    """

    def __init__(
        self,
        config: StorageConfig | None = None,
        sync_client: S3StorageClient | None = None,
    ) -> None:
        """Initialize the async adapter.

        Args:
            config: Optional StorageConfig.
            sync_client: Optional pre-configured synchronous client.
        """
        self.sync_client = sync_client or S3StorageClient(config=config)
        self.config = self.sync_client.config

    async def ensure_buckets_exist(self) -> None:
        """Ensure default buckets exist asynchronously without blocking event loop."""
        await asyncio.to_thread(self.sync_client.ensure_buckets_exist)

    def generate_presigned_upload_url(
        self,
        bucket: str,
        object_name: str,
        expires_seconds: int = 3600,
    ) -> str:
        """Generate presigned PUT URL.

        Note: HMAC calculation is local CPU operation, no thread offloading needed.
        """
        return self.sync_client.generate_presigned_upload_url(
            bucket=bucket,
            object_name=object_name,
            expires_seconds=expires_seconds,
        )

    def generate_presigned_download_url(
        self,
        bucket: str,
        object_name: str,
        expires_seconds: int = 3600,
    ) -> str:
        """Generate presigned GET URL."""
        return self.sync_client.generate_presigned_download_url(
            bucket=bucket,
            object_name=object_name,
            expires_seconds=expires_seconds,
        )

    async def check_health(self) -> bool:
        """Perform MinIO health check without blocking event loop."""
        return await asyncio.to_thread(self.sync_client.check_health)

    async def upload_bytes(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload raw bytes to MinIO asynchronously."""
        await asyncio.to_thread(
            self.sync_client.upload_bytes,
            bucket=bucket,
            object_name=object_name,
            data=data,
            content_type=content_type,
        )

    async def download_bytes(self, bucket: str, object_name: str) -> bytes:
        """Download raw bytes from MinIO asynchronously."""
        return await asyncio.to_thread(
            self.sync_client.download_bytes,
            bucket=bucket,
            object_name=object_name,
        )
