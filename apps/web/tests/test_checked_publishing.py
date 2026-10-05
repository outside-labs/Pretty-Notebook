import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from api import catalog, publish_api
from tortoise import connections


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def payload(name="note", content="<p>First</p>", **extra):
    return {"name": name, "content": content, "source_hash": digest("#public\nFirst\n"),
            "rendered_hash": digest(content), "renderer_fingerprint": digest("renderer-1"), **extra}


def put(client, auth_headers, data=None, etag="*"):
    headers = {**auth_headers, "If-None-Match" if etag == "*" else "If-Match": etag}
    return client.put("/api/publishing/publication", json=data or payload(), headers=headers)


def inventory(client, auth_headers):
    response = client.get("/api/publishing/inventory", headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(("method", "path"), [
    ("get", "/api/publishing/capabilities"), ("get", "/api/publishing/inventory"),
    ("put", "/api/publishing/publication"), ("delete", "/api/publishing/publication/note"),
    ("put", "/api/publishing/image"),
])
def test_revision_api_requires_authentication(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_checked_create_stores_actual_digests_features_and_inventory_etag(client, auth_headers):
    capabilities = client.get("/api/publishing/capabilities", headers=auth_headers)
    assert capabilities.json()["protocol"] == "revision-1"
    data = payload(content='<div class="mermaid">graph TD; A-->B</div>')
    response = put(client, auth_headers, data)
    assert response.status_code == 201
    page, = inventory(client, auth_headers)["pages"]
    assert page["source_hash"] == data["source_hash"]
    assert page["rendered_hash"] == data["rendered_hash"]
    assert page["renderer_fingerprint"] == data["renderer_fingerprint"]
    assert page["feature_flags"] == ["mermaid"]
    assert page["revision"] == 1
    assert page["etag"] == response.headers["etag"] == response.json()["etag"]
    assert response.headers["cache-control"] == "no-store"


def test_checked_updates_reject_stale_heads_and_preserve_legacy_interoperability(client, auth_headers, web_storage):
    original = put(client, auth_headers)
    old = original.headers["etag"]
    changed = put(client, auth_headers, payload(content="<p>Second</p>"), old)
    assert changed.status_code == 200 and changed.json()["revision"] == 2
    blobs = set((web_storage.pages / ".blobs").iterdir())
    assert put(client, auth_headers, payload(content="Stale"), old).status_code == 412
    assert set((web_storage.pages / ".blobs").iterdir()) == blobs
    assert "Second" in client.get("/note").text
    legacy = client.post("/api/publishment", headers=auth_headers, json={"name": "note", "content": "Legacy third"})
    assert legacy.status_code == 201
    assert put(client, auth_headers, payload(), changed.headers["etag"]).status_code == 412
    page, = inventory(client, auth_headers)["pages"]
    assert page["source_hash"] is None and page["renderer_fingerprint"] is None
    assert page["revision"] == 3
    assert put(client, auth_headers, payload(), page["etag"]).status_code == 200


@pytest.mark.parametrize(("headers", "expected"), [
    ({}, 428), ({"If-Match": "*"}, 400), ({"If-Match": 'W/"weak"'}, 400),
    ({"If-Match": '"one", "two"'}, 400), ({"If-Match": "unquoted"}, 400),
    ({"If-None-Match": '"one"'}, 400),
    ({"If-Match": '"one"', "If-None-Match": "*"}, 400),
])
def test_checked_writes_require_one_explicit_precondition(client, auth_headers, headers, expected):
    response = client.put("/api/publishing/publication", json=payload(), headers={**auth_headers, **headers})
    assert response.status_code == expected
    assert inventory(client, auth_headers)["pages"] == []


def test_checked_create_cannot_replace_existing_page_or_uncataloged_legacy_file(client, auth_headers, web_storage):
    assert put(client, auth_headers).status_code == 201
    assert put(client, auth_headers).status_code == 412
    (web_storage.pages / "external.html").write_text("External original")
    assert put(client, auth_headers, payload("external")).status_code == 412
    page = next(page for page in inventory(client, auth_headers)["pages"] if page["pub_name"] == "external.html")
    assert page["etag"] is None and "Restart" in page["detail"]


def test_concurrent_checked_updates_have_one_winner(client, auth_headers):
    etag = put(client, auth_headers).headers["etag"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda body: put(client, auth_headers, payload(content=body), etag), ["Winner A", "Winner B"]))
    assert sorted(response.status_code for response in responses) == [200, 412]
    assert inventory(client, auth_headers)["pages"][0]["revision"] == 2


def test_digest_validation_and_invalid_routes_do_not_write_blobs(client, auth_headers, web_storage):
    assert put(client, auth_headers, payload(rendered_hash="0" * 64)).status_code == 400
    assert put(client, auth_headers, payload(source_hash="invalid")).status_code == 422
    assert put(client, auth_headers, payload(name="api/reserved")).status_code == 400
    assert list(web_storage.pages.iterdir()) == []


def test_checked_route_migration_preserves_identity_and_keeps_collisions_distinct(client, auth_headers):
    created = put(client, auth_headers, payload("old", aliases=["/alias"]))
    first = inventory(client, auth_headers)["pages"][0]
    migrated = put(client, auth_headers, payload("nested/new", previous_name="old"), created.headers["etag"])
    assert migrated.status_code == 200
    page, = inventory(client, auth_headers)["pages"]
    assert page["id"] == first["id"] and page["revision"] == 2
    assert page["aliases"] == ["/alias", "/old"]
    assert client.get("/old", follow_redirects=False).status_code == 308
    assert put(client, auth_headers, payload("other", aliases=["/alias"])).status_code == 409
    assert put(client, auth_headers, payload("other", aliases=["/api"])).status_code == 400


def test_checked_delete_and_recreation_do_not_reuse_old_etags(client, auth_headers):
    old = put(client, auth_headers).headers["etag"]
    path = "/api/publishing/publication/note"
    assert client.delete(path, headers=auth_headers).status_code == 428
    assert client.delete(path, headers={**auth_headers, "If-None-Match": "*"}).status_code == 400
    assert client.delete(path, headers={**auth_headers, "If-Match": old}).status_code == 200
    assert client.delete(path, headers={**auth_headers, "If-Match": old}).status_code == 412
    assert client.get("/note").status_code == 404
    recreated = put(client, auth_headers)
    assert recreated.status_code == 201 and recreated.headers["etag"] != old
    assert put(client, auth_headers, payload(), old).status_code == 412
    assert client.delete("/api/publishing/publication/api/x", headers={**auth_headers, "If-Match": old}).status_code == 400


def test_failed_checked_transaction_preserves_head_and_metadata(client, auth_headers, monkeypatch):
    old = put(client, auth_headers).headers["etag"]
    before = inventory(client, auth_headers)
    original = catalog.PublicationStore._revision
    async def fail_after_insert(self, transaction, *args):
        await original(self, transaction, *args)
        raise OSError("transaction interrupted")
    monkeypatch.setattr(catalog.PublicationStore, "_revision", fail_after_insert)
    assert put(client, auth_headers, payload(content="Not committed"), old).status_code == 500
    assert inventory(client, auth_headers) == before
    assert "First" in client.get("/note").text


def test_precondition_is_rechecked_in_the_revision_transaction(client, auth_headers, monkeypatch):
    old = put(client, auth_headers).headers["etag"]
    original = catalog.PublicationStore._commit_publication
    async def intervene(self, *args, **kwargs):
        await connections.get("default").execute_query("UPDATE pnbp_notes SET title='Intervening change'")
        return await original(self, *args, **kwargs)
    monkeypatch.setattr(catalog.PublicationStore, "_commit_publication", intervene)
    assert put(client, auth_headers, payload(content="Must not commit"), old).status_code == 412
    page, = inventory(client, auth_headers)["pages"]
    assert page["revision"] == 1 and page["title"] == "Intervening change"


def test_checked_images_use_exact_bytes_and_legacy_writes_invalidate_the_etag(client, auth_headers, web_storage):
    data = b"\x89PNG\r\n\x1a\nFirst"
    path = "/api/publishing/image"
    created = client.put(path, headers={**auth_headers, "If-None-Match": "*"}, files={"file": ("photo.png", data)})
    assert created.status_code == 201
    image, = inventory(client, auth_headers)["images"]
    assert image["source_hash"] == digest(data) and image["etag"] == created.headers["etag"]
    assert client.put(path, headers={**auth_headers, "If-None-Match": "*"}, files={"file": ("photo.png", data)}).status_code == 412
    updated = client.put(path, headers={**auth_headers, "If-Match": image["etag"]}, files={"file": ("photo.png", data + b"Second")})
    assert updated.status_code == 200 and updated.headers["etag"] != image["etag"]
    assert client.put(path, headers={**auth_headers, "If-Match": image["etag"]}, files={"file": ("photo.png", data)}).status_code == 412
    assert client.post("/api/image", headers=auth_headers, files={"file": ("photo.png", data + b"Legacy")}).status_code == 201
    assert client.put(path, headers={**auth_headers, "If-Match": updated.headers["etag"]}, files={"file": ("photo.png", data)}).status_code == 412
    assert (web_storage.images / "photo.png").read_bytes() == data + b"Legacy"


def test_checked_images_keep_validation_bounds_and_refuse_symlinks(client, auth_headers, web_storage, monkeypatch, tmp_path):
    headers = {**auth_headers, "If-None-Match": "*"}
    assert client.put("/api/publishing/image", headers=headers, files={"file": ("bad.png", b"bad")}).status_code == 400
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"\x89PNG\r\n\x1a\nOriginal")
    (web_storage.images / "link.png").symlink_to(outside)
    assert client.put("/api/publishing/image", headers=headers, files={"file": ("link.png", outside.read_bytes())}).status_code == 400
    (web_storage.images / "link.png").unlink()
    monkeypatch.setattr(publish_api, "MAX_IMAGE_BYTES", 8)
    assert client.put("/api/publishing/image", headers=headers, files={"file": ("large.png", outside.read_bytes())}).status_code == 413
    (web_storage.images / "large.png").write_bytes(outside.read_bytes())
    assert client.get("/api/publishing/inventory", headers=auth_headers).status_code == 413
