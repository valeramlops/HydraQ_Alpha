"""Configuration module for MinIO S3 storage client."""

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
    )

    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    secure: bool = False
    default_buckets: list[str] = ["datasets", "checkpoints"]
