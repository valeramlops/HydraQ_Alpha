"""Configuration module for MinIO S3 storage client."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageConfig(BaseSettings):
    """MinIO S3 storage configuration loaded from environment variables.

    Attributes:
        endpoint: MinIO server endpoint (host:port).
        access_key: MinIO root user access key.
        secret_key: MinIO root user secret key.
        secure: Whether to use HTTPS for MinIO connections.
        default_buckets: List of buckets to ensure exist on startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    endpoint: str = Field(default="localhost:9000", validation_alias="MINIO_ENDPOINT")
    access_key: str = Field(default="minioadmin", validation_alias="MINIO_ROOT_USER")
    secret_key: str = Field(
        default="minioadmin", validation_alias="MINIO_ROOT_PASSWORD"
    )
    secure: bool = False
    default_buckets: list[str] = ["datasets", "checkpoints"]
