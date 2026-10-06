"""Site titles, PNG favicon validation, caching, persistence and write failures."""

import hashlib
import struct
import zlib
from stat import S_IMODE

import pytest
from api import atomic_io, site_api
from api.png import PNG_SIGNATURE, validate_png
from fastapi.testclient import TestClient
from main import create_app


def chunk(kind, data=b""):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(*, pixel=b"\x00\x20\x40", header=None, data=None, before=(), after=()):
    header = header or struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    data = zlib.compress(b"\x00" + pixel) if data is None else data
    return PNG_SIGNATURE + chunk(b"IHDR", header) + b"".join(before) + chunk(b"IDAT", data) + b"".join(after) + chunk(b"IEND")


def upload(client, headers, image=None, filename="site.png"):
    return client.post("/api/favicon", headers=headers,
                       files={"file": (filename, png() if image is None else image, "image/png")})


def test_upload_serves_png_and_links_versioned_url(client, auth_headers, web_storage):
    image = png()
    response = upload(client, auth_headers, image)
    version = hashlib.sha256(image).hexdigest()
    url = f"/static/favicon/{version}.png"
    assert response.status_code == 201
    assert response.json() == {"url": url, "width": 1, "height": 1}
    assert response.headers["cache-control"] == "no-store"
    assert (web_storage.settings.parent / "favicon.png").read_bytes() == image
    assert S_IMODE((web_storage.settings.parent / "favicon.png").stat().st_mode) == 0o600
    served = client.get(url)
    assert served.content == image
    assert served.headers["content-type"] == "image/png"
    assert served.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert served.headers["etag"] == f'"{version}"'
    assert served.headers["x-content-type-options"] == "nosniff"
    for path in ("/", "/contact", "/missing"):
        assert f'<link rel="icon" type="image/png" href="{url}">' in client.get(path).text
    redirect = client.get("/favicon.ico", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == url
    assert redirect.headers["cache-control"] == "no-store"
    assert client.get("/favicon.ico").content == image


def test_replacement_changes_head_and_redirect_without_stale_content(client, auth_headers):
    first = upload(client, auth_headers).json()["url"]
    old = client.get(first)
    replacement = png(pixel=b"\xff\x00\x80")
    second = upload(client, auth_headers, replacement).json()["url"]
    assert first != second
    assert second in client.get("/").text
    assert first not in client.get("/").text
    assert client.get(second, headers={"If-None-Match": old.headers["etag"]}).content == replacement
    assert client.get(first).status_code == 404
    assert client.get("/favicon.ico", follow_redirects=False).headers["location"] == second


def test_missing_favicon_has_no_head_link_and_returns_404(client):
    assert 'rel="icon"' not in client.get("/").text
    for path in ("/favicon.ico", "/static/favicon/" + "a" * 64 + ".png", "/static/favicon/invalid.png"):
        assert client.get(path, follow_redirects=False).status_code == 404


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_favicon_upload_requires_authentication(client, web_storage, headers):
    assert upload(client, headers).status_code == 401
    assert not (web_storage.settings.parent / "favicon.png").exists()


def test_only_owner_can_manage_site_favicon(client, auth_headers, web_storage):
    credentials = {"username": "editor", "password_hash": "another correct passphrase"}
    assert client.post("/api/users", headers=auth_headers, json=credentials).status_code == 200
    token = client.post("/api/token", data={"username": "editor", "password": credentials["password_hash"]}).json()["access_token"]
    assert upload(client, {"Authorization": f"Bearer {token}"}).status_code == 403
    assert not (web_storage.settings.parent / "favicon.png").exists()


@pytest.mark.parametrize("image,filename", [
    (png(), "site.ico"), (png(), "site.svg"),
    (b"plain text", "site.png"), (PNG_SIGNATURE + b"not pixels", "site.png"),
])
def test_invalid_upload_leaves_previous_favicon_unchanged(client, auth_headers, image, filename):
    previous = upload(client, auth_headers).json()["url"]
    assert upload(client, auth_headers, image, filename).status_code == 400
    assert client.get(previous).content == png()


def test_oversize_upload_is_rejected_before_decoding(client, auth_headers, web_storage, monkeypatch):
    monkeypatch.setattr(site_api, "MAX_FAVICON_BYTES", 16)
    assert upload(client, auth_headers).status_code == 413
    assert not (web_storage.settings.parent / "favicon.png").exists()


@pytest.mark.parametrize("phase", ["write", "replace"])
def test_failed_replacement_preserves_favicon_and_cleans_temporary_files(client, auth_headers, web_storage, monkeypatch, phase):
    previous = upload(client, auth_headers).json()["url"]
    if phase == "replace":
        def fail(*args):
            raise OSError("private filesystem details")
        monkeypatch.setattr(atomic_io, "replace", fail)
    else:
        real_open = atomic_io.aiofiles.open

        class InterruptedWrite:
            def __init__(self, *args, **kwargs):
                self.context = real_open(*args, **kwargs)

            async def __aenter__(self):
                self.output = await self.context.__aenter__()
                return self

            async def write(self, content):
                await self.output.write(content[:5])
                raise OSError("private filesystem details")

            async def __aexit__(self, *exc):
                return await self.context.__aexit__(*exc)

        monkeypatch.setattr(atomic_io.aiofiles, "open", InterruptedWrite)
    failed = upload(client, auth_headers, png(pixel=b"\xff\x00\x80"))
    assert failed.status_code == 500
    assert "private filesystem" not in failed.text
    assert list(web_storage.settings.parent.glob(".favicon.png.*.tmp")) == []
    assert client.get(previous).content == png()


@pytest.mark.parametrize("state", ["corrupt", "directory", "symlink"])
def test_unreadable_or_corrupt_favicon_fails_without_leaking_storage_details(client, web_storage, state):
    target = web_storage.settings.parent / "favicon.png"
    if state == "corrupt":
        target.write_bytes(b"corrupt")
    elif state == "directory":
        target.mkdir()
    else:
        target.symlink_to(web_storage.settings)
    response = client.get("/favicon.ico", follow_redirects=False)
    assert response.status_code == 503
    assert response.json() == {"detail": "Favicon storage is unavailable."}


def test_favicon_survives_restart_and_url_prefix(web_storage, tmp_path, root_credentials, bootstrap_headers):
    database = f"sqlite://{tmp_path / 'site.sqlite3'}"
    with TestClient(create_app(db_url=database, root_path="/notes")) as client:
        client.post("/api/users", json=root_credentials, headers=bootstrap_headers)
        token = client.post("/api/token", data={"username": root_credentials["username"], "password": root_credentials["password_hash"]}).json()["access_token"]
        response = upload(client, {"Authorization": f"Bearer {token}"})
        url = response.json()["url"]
        assert url.startswith("/notes/static/favicon/")
    with TestClient(create_app(db_url=database, root_path="/notes")) as restarted:
        assert url in restarted.get("/notes/").text
        assert restarted.get(url).content == png()
        assert restarted.get("/notes/favicon.ico", follow_redirects=False).headers["location"] == url


def test_page_titles_combine_configured_site_and_publication_titles(client, auth_headers, layout_payload):
    layout_payload["TITLE"] = "Site <title>"
    assert client.post("/api/layout", headers=auth_headers, json=layout_payload).status_code == 201
    assert '<title>Site &lt;title&gt;</title>' in client.get("/").text
    assert '<title>Contact · Site &lt;title&gt;</title>' in client.get("/contact").text
    assert '<title>Page not found · Site &lt;title&gt;</title>' in client.get("/missing").text
    assert '<title>Contact · Site &lt;title&gt;</title>' in client.post("/forms/contact", data={}).text
    assert '<title>Page not found · Site &lt;title&gt;</title>' in client.post("/forms/unknown", data={}).text
    assert client.post("/api/publishment", headers=auth_headers,
                       json={"name": "named", "title": "Note <name>", "content": "<p>Body</p>"}).status_code == 201
    assert '<title>Note &lt;name&gt; · Site &lt;title&gt;</title>' in client.get("/named").text


def test_legacy_page_titles_fall_back_to_route(client, web_storage):
    (web_storage.pages / "legacy.html").write_text("<p>Legacy body</p>")
    assert '<title>legacy · Test notebook</title>' in client.get("/legacy").text


@pytest.mark.parametrize("color,depth,pixel,palette", [
    (0, 1, b"\x00", ()), (0, 16, b"\x00\x00", ()),
    (2, 8, b"\x00\x00\x00", ()), (4, 8, b"\x00\xff", ()),
    (6, 8, b"\x00\x00\x00\xff", ()),
    (3, 1, b"\x00", (chunk(b"PLTE", b"\x00\x00\x00"),)),
])
@pytest.mark.parametrize("interlace", [0, 1])
def test_valid_static_png_profiles_and_interlacing(color, depth, pixel, palette, interlace):
    header = struct.pack(">IIBBBBB", 1, 1, depth, color, 0, 0, interlace)
    assert validate_png(png(header=header, pixel=pixel, before=palette)) == (1, 1)


def test_png_allows_consecutive_data_chunks_and_optional_metadata():
    encoded = zlib.compress(b"\x00\x00\x20\x40")
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    content = PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", encoded[:3]) + chunk(b"IDAT", encoded[3:]) + chunk(b"tEXt", b"Label\x00Example") + chunk(b"IEND")
    assert validate_png(content) == (1, 1)


def test_adam7_passes_are_validated_for_a_larger_image():
    header = struct.pack(">IIBBBBB", 3, 3, 8, 0, 0, 0, 1)
    assert validate_png(png(header=header, data=zlib.compress(b"\x00" * 15))) == (3, 3)


@pytest.mark.parametrize("content", [
    b"", PNG_SIGNATURE, PNG_SIGNATURE + b"truncated",
    png()[:-1], png() + b"trailing", png()[:-12],
    PNG_SIGNATURE + chunk(b"IDAT", b"bad") + chunk(b"IEND"),
    png(before=(chunk(b"IHDR", b"bad"),)),
    png(header=b"short"),
    png(header=struct.pack(">IIBBBBB", 0, 1, 8, 2, 0, 0, 0)),
    png(header=struct.pack(">IIBBBBB", 513, 1, 8, 2, 0, 0, 0)),
    png(header=struct.pack(">IIBBBBB", 1, 1, 8, 2, 1, 0, 0)),
    png(header=struct.pack(">IIBBBBB", 1, 1, 1, 2, 0, 0, 0)),
    png(before=(chunk(b"PLTE", b"bad-length"),)),
    png(header=struct.pack(">IIBBBBB", 1, 1, 8, 3, 0, 0, 0)),
    png(before=(chunk(b"PLTE", b"\x00\x00\x00"), chunk(b"PLTE", b"\x00\x00\x00"))),
    png(before=(chunk(b"ABCD", b"unknown critical"),)),
    png(before=(chunk(b"abcd", b"invalid reserved bit"),)),
    png(before=(chunk(b"a1Cd", b"invalid type"),)),
    png(before=(chunk(b"acTL", struct.pack(">II", 2, 0)),)),
    png(after=(chunk(b"tEXt", b"key\x00value"), chunk(b"IDAT", b"more"))),
    png(after=(chunk(b"IEND", b"unexpected data"),)),
    png(data=b"not zlib"), png(data=zlib.compress(b"too much pixel data")),
    png(data=zlib.compress(b"\x00\x00\x20\x40") + b"extra"),
    png(data=zlib.compress(b"\xff\x00\x20\x40")),
    png()[:29] + b"\xff" + png()[30:],
])
def test_invalid_png_streams_are_rejected(content):
    with pytest.raises(ValueError):
        validate_png(content)


def test_compressed_png_bomb_is_bounded():
    with pytest.raises(ValueError, match="pixel-data length"):
        validate_png(png(data=zlib.compress(b"\x00" * 4_000_000)))


def test_validator_rejects_oversize_content():
    with pytest.raises(ValueError, match="1 MiB"):
        validate_png(png() + b"x" * (1024 * 1024))
