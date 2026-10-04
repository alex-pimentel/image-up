"""Cloudflare R2 (S3-compatible) storage helper.

Only this module talks to boto3. It is deliberately import-safe: boto3 is
imported lazily inside :attr:`R2Storage.client` so unit tests can inject a fake
client and environments without boto3 can still import the app.

Key convention (spec C §7):
    tmp/uploads/{service}/{task_id}/{filename}
    tmp/results/{service}/{task_id}/{filename}
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SERVICE = "imageup"


def upload_key(task_id: str, filename: str) -> str:
    return f"tmp/uploads/{SERVICE}/{task_id}/{filename}"


def result_key(task_id: str, filename: str = "result.webp") -> str:
    return f"tmp/results/{SERVICE}/{task_id}/{filename}"


class R2Storage:
    """Thin wrapper around the S3 API for the private ``tmp`` bucket."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint: str,
        access_key_id: str,
        secret_access_key: str,
        presign_expiry_sec: int = 900,
        client: Any | None = None,
    ) -> None:
        self._bucket = bucket
        self._endpoint = endpoint
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._presign_expiry_sec = presign_expiry_sec
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3  # imported lazily so tests / fallback mode don't need it

            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._secret_access_key,
                region_name="auto",
            )
        return self._client

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> None:
        kwargs: dict[str, Any] = {"Bucket": self._bucket, "Key": key, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        self.client.put_object(**kwargs)

    def put_file(self, key: str, path: Path, content_type: str | None = None) -> None:
        kwargs: dict[str, Any] = {}
        if content_type:
            kwargs["ExtraArgs"] = {"ContentType": content_type}
        self.client.upload_file(str(path), self._bucket, key, **kwargs)

    def download_file(self, key: str, dest: Path) -> None:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self._bucket, key, str(dest))

    def get_bytes(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()

    def presigned_get_url(self, key: str, expires_in: int | None = None) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in or self._presign_expiry_sec,
        )
