from datetime import datetime

import pytest
from api import publish_api, catalog


def test_publication_create_list_and_delete_lifecycle(
    client,
    auth_headers,
    web_storage,
):
    response = client.post(
        "/api/publishment",
        headers=auth_headers,
        json={"name": "hello-world", "content": "<h1>Hello</h1>"},
    )

    assert response.status_code == 201
    publication = response.json()
    assert publication["name"] == "hello-world"
    assert publication["content"] == "<h1>Hello</h1>"
    assert publication["content"] in client.get("/hello-world").text
    assert not (web_storage.pages / "hello-world.html").exists()
    assert len(list((web_storage.pages / ".blobs").glob("*.html"))) == 1

    listing = client.get("/api/publishments", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["pub_name"] == "hello-world.html"
    assert datetime.fromisoformat(listing.json()[0]["mod_date"]).tzinfo is not None

    deleted = client.delete(
        "/api/publishment/hello-world.html",
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json() == {"pub_name": "hello-world.html"}
    assert not (web_storage.pages / "hello-world.html").exists()
    assert client.get("/hello-world").status_code == 404
    assert len(list((web_storage.pages / ".blobs").glob("*.html"))) == 1

    missing = client.delete(
        "/api/publishment/hello-world.html",
        headers=auth_headers,
    )
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Publication not found."}


def test_publication_post_replaces_existing_content(
    client,
    auth_headers,
    web_storage,
):
    first = client.post(
        "/api/publishment",
        headers=auth_headers,
        json={"name": "updated-note", "content": "first version"},
    )
    second = client.post(
        "/api/publishment",
        headers=auth_headers,
        json={"name": "updated-note", "content": "second version"},
    )

    saved = client.get("/updated-note").text
    assert first.status_code == 201
    assert second.status_code == 201
    assert "second version" in saved
    assert "first version" not in saved


@pytest.mark.parametrize(
    "name",
    ["", "../escape", "nested//name", "Uppercase", "has space", "note.html"],
)
def test_publication_create_rejects_invalid_slugs(
    client,
    auth_headers,
    web_storage,
    name,
):
    response = client.post(
        "/api/publishment",
        headers=auth_headers,
        json={"name": name, "content": "body"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid publication name."}
    assert list(web_storage.pages.iterdir()) == []


@pytest.mark.parametrize("payload", [{}, {"name": "note"}, {"content": "body"}])
def test_publication_create_rejects_malformed_payloads(client, auth_headers, payload):
    response = client.post(
        "/api/publishment",
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "filename",
    ["../note.html", "nested/note.html", "note.txt", "note"],
)
def test_publication_delete_rejects_invalid_filenames(client, auth_headers, filename):
    response = client.delete(
        f"/api/publishment/{filename}",
        headers=auth_headers,
    )

    assert response.status_code in {400, 404}
    assert response.status_code != 200


def test_image_create_and_list_lifecycle(client, auth_headers, web_storage):
    image_bytes = b"\x89PNG\r\n\x1a\npretty-notebook"
    response = client.post(
        "/api/image",
        headers=auth_headers,
        files={"file": ("diagram.PNG", image_bytes, "image/png")},
    )

    assert response.status_code == 201
    assert response.json() == {"filename": "diagram.PNG"}
    assert (web_storage.images / "diagram.PNG").read_bytes() == image_bytes

    listing = client.get("/api/images", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["img_name"] == "diagram.PNG"
    assert datetime.fromisoformat(listing.json()[0]["mod_date"]).tzinfo is not None


@pytest.mark.parametrize(
    ("filename", "expected_detail"),
    [
        ("../escape.png", "Invalid filename."),
        ("nested/image.png", "Invalid filename."),
        ("document.txt", "Unsupported image type."),
    ],
)
def test_image_create_rejects_invalid_filenames(
    client,
    auth_headers,
    web_storage,
    filename,
    expected_detail,
):
    response = client.post(
        "/api/image",
        headers=auth_headers,
        files={"file": (filename, b"contents", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": expected_detail}
    assert list(web_storage.images.iterdir()) == []


def test_image_create_rejects_content_that_does_not_match_extension(
    client,
    auth_headers,
    web_storage,
):
    response = client.post(
        "/api/image",
        headers=auth_headers,
        files={"file": ("not-really.png", b"plain text", "image/png")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File content does not match its image type."}
    assert list(web_storage.images.iterdir()) == []


def test_image_create_enforces_size_limit(
    client,
    auth_headers,
    web_storage,
    monkeypatch,
):
    monkeypatch.setattr(publish_api, "MAX_IMAGE_BYTES", 8)
    response = client.post(
        "/api/image",
        headers=auth_headers,
        files={"file": ("large.png", b"\x89PNG\r\n\x1a\nX", "image/png")},
    )

    assert response.status_code == 413
    assert response.json() == {"detail": "Image exceeds the 10 MiB limit."}
    assert list(web_storage.images.iterdir()) == []


def test_lists_ignore_unmanaged_files(client, auth_headers, web_storage):
    (web_storage.pages / "managed.html").write_text("managed", encoding="utf-8")
    (web_storage.pages / "README.txt").write_text("ignored", encoding="utf-8")
    (web_storage.images / "managed.webp").write_bytes(b"managed")
    (web_storage.images / "ignored.svg").write_bytes(b"ignored")

    publications = client.get("/api/publishments", headers=auth_headers).json()
    images = client.get("/api/images", headers=auth_headers).json()

    assert [item["pub_name"] for item in publications] == ["managed.html"]
    assert [item["img_name"] for item in images] == ["managed.webp"]


def test_publication_storage_failure_returns_server_error(
    client,
    auth_headers,
    web_storage,
    monkeypatch,
):
    def fail_write(*args, **kwargs):
        raise OSError("simulated storage failure")

    monkeypatch.setattr(catalog, "_write_blob", fail_write)
    response = client.post(
        "/api/publishment",
        headers=auth_headers,
        json={"name": "unwritten", "content": "body"},
    )

    assert response.status_code == 500
    assert not (web_storage.pages / "unwritten.html").exists()
