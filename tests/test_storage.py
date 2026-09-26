"""Integration tests for libs/storage against a live MinIO container."""

import httpx
import pytest

from libs.storage import S3StorageClient, StorageConfig

PAYLOAD = b"HydraQ-Quantum-Payload-Test"
TEST_OBJECT_KEY = "test/synthetic_lorenz.bin"


@pytest.fixture(scope="module")
def storage_client():
    config = StorageConfig()
    client = S3StorageClient(config)
    client.ensure_buckets_exist()
    return client


def test_storage_healthcheck(storage_client):
    assert storage_client.check_health() is True


def test_ensure_buckets_exist(storage_client):
    for bucket_name in storage_client.config.default_buckets:
        assert storage_client.client.bucket_exists(bucket_name)


def test_presigned_upload_and_download_flow(storage_client):
    upload_url = storage_client.generate_presigned_upload_url(
        bucket="datasets",
        object_name=TEST_OBJECT_KEY,
    )
    assert upload_url.startswith("http")

    upload_response = httpx.put(upload_url, content=PAYLOAD)
    assert upload_response.status_code == 200

    download_url = storage_client.generate_presigned_download_url(
        bucket="datasets",
        object_name=TEST_OBJECT_KEY,
    )
    assert download_url.startswith("http")

    download_response = httpx.get(download_url)
    assert download_response.status_code == 200
    assert download_response.content == PAYLOAD


def test_direct_bytes_upload_download(storage_client):
    object_key = "test/direct_bytes_payload.bin"

    storage_client.upload_bytes(
        bucket="checkpoints",
        object_name=object_key,
        data=PAYLOAD,
        content_type="application/octet-stream",
    )

    downloaded = storage_client.download_bytes(
        bucket="checkpoints",
        object_name=object_key,
    )
    assert downloaded == PAYLOAD
