import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from api import publishing_api
from pnbp import Notebook, _publication_plan as plans


class RequestsResponse:
    def __init__(self, response):
        self.response = response
        self.status_code, self.headers = response.status_code, response.headers

    def json(self):
        return self.response.json()

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


@pytest.fixture
def publishing_transport(client, monkeypatch):
    class Transport:
        def __init__(self):
            self.calls = []
            self.before_put = None
            self.lose_page = False

        def call(self, method, url, **kwargs):
            assert kwargs.pop("timeout") == Notebook.REQUEST_TIMEOUT
            self.calls.append((method, urlsplit(url).path))
            if method == "PUT" and self.before_put:
                callback, self.before_put = self.before_put, None
                callback()
            response = client.request(method, url, **kwargs)
            if method == "PUT" and url.endswith("/publication") and self.lose_page and response.status_code < 400:
                self.lose_page = False
                raise requests.ConnectionError("response lost after commit")
            return RequestsResponse(response)
    transport = Transport()
    for method in ("get", "post", "put", "delete"):
        def send(url, _method=method.upper(), **kwargs):
            return transport.call(_method, url, **kwargs)
        monkeypatch.setattr(requests, method, send)
    return transport


@pytest.fixture
def notebook(tmp_path, client, auth_headers):
    root, images = tmp_path / "local-notes", tmp_path / "local-images"
    root.mkdir()
    images.mkdir()
    (root / "note.md").write_bytes(b"#public\r\n```mermaid\r\ngraph TD; A-->B\r\n```\r\n![[photo.png]]\r\n")
    (images / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\nFirst")
    return Notebook(root, settings={"API_BASE": str(client.base_url).rstrip("/"), "IMG_PATH": str(images)},
                    api_token=auth_headers["Authorization"].split(" ", 1)[1], settings_file="off")


def inventory(client, auth_headers):
    response = client.get("/api/publishing/inventory", headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_actual_checked_client_server_hashes_revisions_images_and_noop_retry(notebook, publishing_transport, client, auth_headers, web_storage):
    root = Path(notebook.NOTE_PATH)
    assert notebook.publication_plan()["pages"][0]["action"] == "create"
    assert not (root / ".pnbp").exists()
    notebook.post_commits_to_web_api(mode="checked")
    page, = inventory(client, auth_headers)["pages"]
    assert page["source_hash"] == plans.digest((root / "note.md").read_bytes())
    assert page["feature_flags"] == ["code", "mermaid"] and page["revision"] == 1
    assert page["rendered_hash"] == plans.digest(notebook.convert_to_html(notebook.notes["note"]).encode())
    assert (web_storage.images / "photo.png").read_bytes() == (Path(notebook.IMG_PATH) / "photo.png").read_bytes()
    receipts = json.loads((root / ".pnbp" / "sync.json").read_text())
    assert receipts["targets"][notebook.API_BASE]["pages"]["note.html"]["etag"] == page["etag"]
    writes = sum(method in {"PUT", "DELETE"} for method, _ in publishing_transport.calls)
    notebook.post_commits_to_web_api()
    assert sum(method in {"PUT", "DELETE"} for method, _ in publishing_transport.calls) == writes
    source = root / "note.md"
    stamp = source.stat().st_mtime
    source.write_bytes(source.read_bytes() + b"Changed at equal time\r\n")
    os.utime(source, (stamp, stamp))
    (Path(notebook.IMG_PATH) / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\nSecond")
    notebook.post_commits_to_web_api()
    assert inventory(client, auth_headers)["pages"][0]["revision"] == 2
    assert (web_storage.images / "photo.png").read_bytes().endswith(b"Second")


def test_actual_server_stale_revision_cannot_be_overwritten_or_pruned(notebook, publishing_transport, client, auth_headers):
    notebook.post_commits_to_web_api()
    client.post("/api/publishment", headers=auth_headers, json={"name": "unlisted", "content": "Preserve"})
    (Path(notebook.NOTE_PATH) / "note.md").write_text("#public\nLocal changed")
    def concurrent_update():
        response = client.post("/api/publishment", headers=auth_headers, json={"name": "note", "content": "Concurrent winner"})
        assert response.status_code == 201
    publishing_transport.before_put = concurrent_update
    with pytest.raises(requests.HTTPError, match="412"):
        notebook.post_commits_to_web_api(prune=True)
    assert "Concurrent winner" in client.get("/note").text
    assert client.get("/unlisted").status_code == 200
    assert not any(method == "DELETE" for method, _ in publishing_transport.calls)
    assert notebook.publication_plan()["pages"][0]["action"] == "conflict"


def test_actual_lost_response_recovery_and_image_storage_failure_stop_before_prune(notebook, publishing_transport, client, auth_headers, monkeypatch):
    publishing_transport.lose_page = True
    with pytest.raises(requests.ConnectionError):
        notebook.post_commits_to_web_api()
    assert inventory(client, auth_headers)["pages"][0]["revision"] == 1
    notebook.post_commits_to_web_api()
    assert inventory(client, auth_headers)["pages"][0]["revision"] == 1
    client.post("/api/publishment", headers=auth_headers, json={"name": "unlisted", "content": "Keep"})
    (Path(notebook.IMG_PATH) / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\nNew image")
    async def fail_write(*args):
        raise OSError("image storage unavailable")
    monkeypatch.setattr(publishing_api, "atomic_write_bytes", fail_write)
    with pytest.raises(requests.HTTPError, match="500"):
        notebook.post_commits_to_web_api(prune=True)
    assert client.get("/unlisted").status_code == 200
    assert not any(method == "DELETE" for method, _ in publishing_transport.calls)
