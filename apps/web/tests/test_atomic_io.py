import asyncio
from concurrent.futures import ThreadPoolExecutor
from stat import S_IMODE
from threading import Event

import pytest
from api import atomic_io, catalog


def assert_no_temporary_file(target):
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []


def test_failed_publication_blob_write_preserves_existing_page(
    client, auth_headers, web_storage, monkeypatch
):
    target = web_storage.pages / "existing.html"
    target.write_text("old page", encoding="utf-8")

    def fail_replace(*args):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(catalog.os, "link", fail_replace)
    response = client.post(
        "/api/publishment",
        headers=auth_headers,
        json={"name": "existing", "content": "new page"},
    )

    assert response.status_code == 500
    assert target.read_text(encoding="utf-8") == "old page"
    assert_no_temporary_file(target)
    assert "old page" in client.get("/existing").text
    assert list((web_storage.pages / ".blobs").glob(".body-*.tmp")) == []


def test_failed_layout_replace_preserves_existing_settings(
    client, auth_headers, layout_payload, web_storage, monkeypatch
):
    target = web_storage.settings
    original = target.read_text(encoding="utf-8")

    def fail_replace(*args):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(atomic_io, "replace", fail_replace)
    response = client.post(
        "/api/layout",
        headers=auth_headers,
        json={**layout_payload, "TITLE": "Changed"},
    )

    assert response.status_code == 500
    assert target.read_text(encoding="utf-8") == original
    assert_no_temporary_file(target)


def test_failed_image_replace_preserves_existing_image(
    client, auth_headers, web_storage, monkeypatch
):
    target = web_storage.images / "existing.png"
    target.write_bytes(b"\x89PNG\r\n\x1a\nold")

    def fail_replace(*args):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(atomic_io, "replace", fail_replace)
    response = client.post(
        "/api/image",
        headers=auth_headers,
        files={"file": ("existing.png", b"\x89PNG\r\n\x1a\nnew", "image/png")},
    )

    assert response.status_code == 500
    assert target.read_bytes() == b"\x89PNG\r\n\x1a\nold"
    assert_no_temporary_file(target)


def test_partial_temporary_write_preserves_existing_file(
    web_storage, monkeypatch
):
    target = web_storage.settings
    original = target.read_text(encoding="utf-8")
    real_open = atomic_io.aiofiles.open

    class FailingOpen:
        def __init__(self, *args, **kwargs):
            self.context = real_open(*args, **kwargs)

        async def __aenter__(self):
            self.output = await self.context.__aenter__()
            return self

        async def write(self, content):
            await self.output.write(content[:5])
            raise OSError("simulated interrupted write")

        async def __aexit__(self, *exc):
            return await self.context.__aexit__(*exc)

    monkeypatch.setattr(atomic_io.aiofiles, "open", FailingOpen)

    with pytest.raises(OSError, match="simulated interrupted write"):
        asyncio.run(atomic_io.atomic_write_text(target, "new settings"))

    assert target.read_text(encoding="utf-8") == original
    assert_no_temporary_file(target)


def test_replacement_keeps_existing_file_permissions(web_storage):
    target = web_storage.settings
    target.chmod(0o640)

    asyncio.run(atomic_io.atomic_write_text(target, "new settings"))

    assert S_IMODE(target.stat().st_mode) == 0o640


@pytest.mark.parametrize("storage_name", ["page", "layout"])
def test_reader_sees_complete_file_during_replacement(
    web_storage, monkeypatch, storage_name
):
    target = (
        web_storage.pages / "concurrent.html"
        if storage_name == "page"
        else web_storage.settings
    )
    old = "old content " * 1000
    new = "new content " * 1000
    target.write_text(old, encoding="utf-8")
    ready = Event()
    release = Event()
    real_replace = atomic_io.replace

    def paused_replace(source, destination):
        ready.set()
        if not release.wait(timeout=5):
            raise TimeoutError("replacement was never released")
        real_replace(source, destination)

    monkeypatch.setattr(atomic_io, "replace", paused_replace)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            lambda: asyncio.run(atomic_io.atomic_write_text(target, new))
        )
        try:
            assert ready.wait(timeout=5)
            assert {target.read_text(encoding="utf-8") for _ in range(20)} == {old}
        finally:
            release.set()
        future.result(timeout=5)

    assert {target.read_text(encoding="utf-8") for _ in range(20)} == {new}
    assert_no_temporary_file(target)


def test_first_settings_publish_is_complete_and_private(tmp_path, monkeypatch):
    from api import atomic_io
    target = tmp_path / 'web-settings.json'
    content = '{"TITLE": "Complete defaults"}'
    original_link = atomic_io.link
    def observe_publish(source, destination):
        assert not target.exists()
        assert source.read_text() == content
        original_link(source, destination)
    monkeypatch.setattr(atomic_io, 'link', observe_publish)
    assert atomic_io.create_text_once(target, content) is True
    assert target.read_text() == content
    assert target.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.glob('.*.tmp')) == []


def test_competing_initialization_preserves_the_winner_and_its_mode(tmp_path, monkeypatch):
    from api import atomic_io
    target = tmp_path / 'web-settings.json'
    original_link = atomic_io.link
    def competing_publish(source, destination):
        target.write_text('Owner settings')
        target.chmod(0o640)
        original_link(source, destination)
    monkeypatch.setattr(atomic_io, 'link', competing_publish)
    assert atomic_io.create_text_once(target, 'Default settings') is False
    assert target.read_text() == 'Owner settings'
    assert target.stat().st_mode & 0o777 == 0o640
    assert list(tmp_path.glob('.*.tmp')) == []
