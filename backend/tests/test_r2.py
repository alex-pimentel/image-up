"""Unit tests for the R2 storage helper (boto3 client mocked, no network)."""
from __future__ import annotations

from pathlib import Path

from app.services.r2 import R2Storage, result_key, upload_key

BUCKET = "agenteresolve-tmp"


class FakeS3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.objects: dict[str, bytes] = {}

    def put_object(self, **kwargs):
        self.calls.append(("put_object", kwargs))
        self.objects[kwargs["Key"]] = kwargs["Body"]
        return {}

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        self.calls.append(
            ("upload_file", {"Filename": filename, "Bucket": bucket, "Key": key, "ExtraArgs": ExtraArgs})
        )
        self.objects[key] = Path(filename).read_bytes()

    def download_file(self, bucket, key, filename):
        self.calls.append(("download_file", {"Bucket": bucket, "Key": key, "Filename": filename}))
        Path(filename).write_bytes(self.objects[key])

    def generate_presigned_url(self, operation, Params=None, ExpiresIn=None):
        self.calls.append(
            ("generate_presigned_url", {"operation": operation, "Params": Params, "ExpiresIn": ExpiresIn})
        )
        return f"https://r2.example/{Params['Key']}?sig=abc"

    def get_object(self, **kwargs):
        self.calls.append(("get_object", kwargs))

        class Body:
            def __init__(self, data: bytes) -> None:
                self._data = data

            def read(self) -> bytes:
                return self._data

        return {"Body": Body(self.objects[kwargs["Key"]])}


def make_storage() -> tuple[R2Storage, FakeS3Client]:
    client = FakeS3Client()
    storage = R2Storage(
        bucket=BUCKET,
        endpoint="https://acct.r2.cloudflarestorage.com",
        access_key_id="id",
        secret_access_key="secret",
        presign_expiry_sec=120,
        client=client,
    )
    return storage, client


def test_key_conventions() -> None:
    assert upload_key("abc", "photo.png") == "tmp/uploads/imageup/abc/photo.png"
    assert result_key("abc") == "tmp/results/imageup/abc/result.webp"
    assert result_key("abc", "result.png") == "tmp/results/imageup/abc/result.png"


def test_put_bytes_uses_bucket_and_content_type() -> None:
    storage, client = make_storage()
    storage.put_bytes("tmp/uploads/imageup/abc/photo.png", b"data", content_type="image/png")
    op, kwargs = client.calls[-1]
    assert op == "put_object"
    assert kwargs == {
        "Bucket": BUCKET,
        "Key": "tmp/uploads/imageup/abc/photo.png",
        "Body": b"data",
        "ContentType": "image/png",
    }


def test_put_bytes_without_content_type_omits_header() -> None:
    storage, client = make_storage()
    storage.put_bytes("tmp/uploads/imageup/abc/photo.png", b"data")
    _, kwargs = client.calls[-1]
    assert "ContentType" not in kwargs


def test_put_file_passes_extra_args(tmp_path: Path) -> None:
    src = tmp_path / "result.webp"
    src.write_bytes(b"webp-bytes")
    storage, client = make_storage()
    storage.put_file("tmp/results/imageup/abc/result.webp", src, content_type="image/webp")
    op, kwargs = client.calls[-1]
    assert op == "upload_file"
    assert kwargs["Key"] == "tmp/results/imageup/abc/result.webp"
    assert kwargs["ExtraArgs"] == {"ContentType": "image/webp"}


def test_download_file_creates_parent_dirs(tmp_path: Path) -> None:
    storage, client = make_storage()
    client.objects["tmp/uploads/imageup/abc/photo.png"] = b"original"
    dest = tmp_path / "nested" / "photo.png"
    storage.download_file("tmp/uploads/imageup/abc/photo.png", dest)
    assert dest.read_bytes() == b"original"


def test_presigned_get_url_is_short_lived() -> None:
    storage, client = make_storage()
    url = storage.presigned_get_url("tmp/results/imageup/abc/result.webp")
    op, kwargs = client.calls[-1]
    assert op == "generate_presigned_url"
    assert kwargs["operation"] == "get_object"
    assert kwargs["Params"] == {"Bucket": BUCKET, "Key": "tmp/results/imageup/abc/result.webp"}
    assert kwargs["ExpiresIn"] == 120
    assert url.startswith("https://")


def test_get_bytes_reads_body() -> None:
    storage, client = make_storage()
    client.objects["tmp/results/imageup/abc/result.webp"] = b"bytes"
    assert storage.get_bytes("tmp/results/imageup/abc/result.webp") == b"bytes"
