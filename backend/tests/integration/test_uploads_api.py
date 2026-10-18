"""Serving uploaded files: what the browser gets, and what it must not."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.core.config import get_settings

PNG = b"\x89PNG\r\n\x1a\n fake image"


@pytest.fixture()
def upload_root() -> Path:
    root = Path(get_settings().upload_root)
    (root / "forum").mkdir(parents=True, exist_ok=True)
    (root / "forum" / "a.png").write_bytes(PNG)
    yield root
    (root / "forum" / "a.png").unlink(missing_ok=True)


@pytest.fixture()
def sibling_secret(upload_root) -> Path:
    # A directory next to the upload root whose name starts with the root's
    # name, such as an "uploads_backup" someone made by hand.
    sibling = upload_root.parent / f"{upload_root.name}_secret"
    sibling.mkdir(exist_ok=True)
    (sibling / "secret.txt").write_text("not for the browser")
    yield sibling
    shutil.rmtree(sibling)


def _assert_not_found(response) -> None:
    assert response.status_code == 404, response.content
    assert response.json() == {"code": 40400, "message": "Uploaded file not found.", "data": {}}


class TestServing:
    def test_serves_the_file_with_its_type(self, client, upload_root):
        response = client.get("/api/uploads/forum/a.png")

        assert response.status_code == 200
        assert response.content == PNG
        assert response.headers["content-type"] == "image/png"
        assert response.headers["content-length"] == str(len(PNG))
        assert response.headers["accept-ranges"] == "bytes"
        assert response.headers["last-modified"]
        # Browsers revalidate every time, so a replaced file shows up at once.
        assert response.headers["cache-control"] == "no-cache"

    def test_head_sends_the_headers_without_the_body(self, client, upload_root):
        response = client.head("/api/uploads/forum/a.png")

        assert response.status_code == 200
        assert response.content == b""
        assert response.headers["content-length"] == str(len(PNG))

    def test_a_cached_copy_is_revalidated_with_the_etag(self, client, upload_root):
        etag = client.get("/api/uploads/forum/a.png").headers["etag"]

        response = client.get("/api/uploads/forum/a.png", headers={"If-None-Match": etag})

        assert response.status_code == 304
        assert response.content == b""

    def test_a_cached_copy_is_revalidated_with_its_date(self, client, upload_root):
        last_modified = client.get("/api/uploads/forum/a.png").headers["last-modified"]

        response = client.get(
            "/api/uploads/forum/a.png", headers={"If-Modified-Since": last_modified}
        )

        assert response.status_code == 304

    def test_a_changed_file_is_sent_again(self, client, upload_root):
        response = client.get("/api/uploads/forum/a.png", headers={"If-None-Match": '"stale"'})

        assert response.status_code == 200
        assert response.content == PNG

    def test_a_range_request_gets_part_of_the_file(self, client, upload_root):
        response = client.get("/api/uploads/forum/a.png", headers={"Range": "bytes=0-3"})

        assert response.status_code == 206
        assert response.content == PNG[:4]
        assert response.headers["content-range"] == f"bytes 0-3/{len(PNG)}"

    def test_a_missing_file_is_not_found(self, client, upload_root):
        _assert_not_found(client.get("/api/uploads/forum/missing.png"))

    def test_a_directory_is_not_found(self, client, upload_root):
        _assert_not_found(client.get("/api/uploads/forum"))

    def test_another_method_is_not_allowed(self, client, upload_root):
        response = client.post("/api/uploads/forum/a.png")

        assert response.status_code == 405
        assert response.json()["code"] == 40500


class TestStaysInsideTheUploadRoot:
    @pytest.mark.parametrize(
        "path",
        [
            "..%2F{sibling}/secret.txt",
            "%2E%2E/{sibling}/secret.txt",
        ],
    )
    def test_a_sibling_directory_sharing_the_prefix(self, client, sibling_secret, path):
        _assert_not_found(client.get("/api/uploads/" + path.format(sibling=sibling_secret.name)))

    def test_climbing_out_of_the_root(self, client, upload_root):
        _assert_not_found(client.get("/api/uploads/..%2F..%2Fpyproject.toml"))

    def test_an_absolute_path(self, client, sibling_secret):
        target = (sibling_secret / "secret.txt").as_posix()
        _assert_not_found(client.get("/api/uploads/" + target.replace(":", "%3A")))
