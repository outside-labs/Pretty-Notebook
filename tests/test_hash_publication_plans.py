import json
import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import requests

from pretty_notebook import Notebook
from pretty_notebook._internal import publication_plan as plans

SERVER_ID = "a02a9862-f303-41b8-baa0-ef6c1eb04e3f"
NOTE_ID = "71630f18-f7b5-41eb-92df-2ad5a92b61cc"


class Response:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class Remote:
    def __init__(self, monkeypatch):
        self.capabilities = {"protocol": "revision-1", "content_hashes": True,
                             "checked_publications": True, "checked_images": True, "single_notebook": True}
        self.status = 200
        self.pages, self.images, self.calls = [], [], []
        self.routes = {"valid": True, "conflicts": []}
        monkeypatch.setattr(requests, "get", self.get)
        monkeypatch.setattr(requests, "post", self.post)

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        if url.endswith("/api/publishing/capabilities"):
            return Response(self.capabilities, self.status)
        if url.endswith("/api/publishing/inventory"):
            return Response({"notebook_id": SERVER_ID, "pages": self.pages, "images": self.images})
        if url.endswith(("/api/publishments", "/api/images")):
            return Response([])
        raise AssertionError(f"Unexpected GET: {url}")

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        assert url.endswith("/api/routes/preview")
        return Response(self.routes)

    def matching(self, page):
        return {"pub_name": page.name, "etag": '"revision-1"', "revision": 1,
                "id": NOTE_ID, "notebook_id": SERVER_ID, "title": page.title, "aliases": list(page.aliases),
                "source_hash": page.source_hash, "rendered_hash": page.rendered_hash,
                "renderer_fingerprint": page.renderer_fingerprint}


@pytest.fixture
def local(tmp_path):
    root, images = tmp_path / "notes", tmp_path / "images"
    root.mkdir()
    images.mkdir()
    (root / "note.md").write_bytes(b"#public\r\nHello.\r\n")
    return Notebook(root, settings={"API_BASE": "https://publish.example", "IMG_PATH": str(images)}, settings_file="off")


@pytest.fixture
def remote(monkeypatch):
    return Remote(monkeypatch)


def test_plan_hashes_exact_bytes_and_is_immutable_redacted_and_read_only(local, remote):
    root = Path(local.NOTE_PATH)
    before = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    local.API_TOKEN = "test-only-private-token"
    plan = local.prepare_publication()
    page, = plan.pages
    assert page.action == "create" and page.expected_etag is None
    assert page.source_hash == plans.digest(b"#public\r\nHello.\r\n")
    assert page.rendered_hash == plans.digest(page.content.encode())
    assert plan.server_notebook_id == SERVER_ID and plan.notebook_id is None
    assert plan.root == str(root) and plan.target == local.API_BASE
    assert not (root / ".pnbp").exists()
    assert before == {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    serialized = json.dumps(plan.preview())
    assert "private-token" not in serialized and "Hello." not in serialized
    assert "private-token" not in repr(plan)
    with pytest.raises(FrozenInstanceError):
        plan.target = "https://other.example"
    assert all(call[2]["timeout"] == local.REQUEST_TIMEOUT for call in remote.calls)
    assert {call[1].rsplit("/", 1)[-1] for call in remote.calls} == {"capabilities", "inventory", "preview"}


def test_changed_bytes_with_equal_timestamp_update_and_identical_newer_bytes_skip(local, remote):
    remote.pages = [remote.matching(local.prepare_publication().pages[0])]
    path = Path(local.NOTE_PATH) / "note.md"
    stamp = path.stat().st_mtime
    os.utime(path, (stamp + 1000, stamp + 1000))
    assert local.prepare_publication().pages[0].action == "unchanged"
    path.write_bytes(b"#public\r\nChanged.\r\n")
    os.utime(path, (stamp, stamp))
    changed = local.prepare_publication().pages[0]
    assert changed.action == "update" and changed.expected_etag == '"revision-1"'


def test_renderer_settings_actual_html_and_link_changes_regenerate(local, remote):
    original = local.prepare_publication().pages[0]
    remote.pages = [remote.matching(original)]
    local.config["HIDE_COMMIT_TAG"] = True
    changed = local.prepare_publication().pages[0]
    assert changed.action == "update" and changed.renderer_fingerprint != original.renderer_fingerprint
    local.config.pop("HIDE_COMMIT_TAG")
    remote.pages[0]["rendered_hash"] = "0" * 64
    assert local.prepare_publication().pages[0].action == "update"
    root = Path(local.NOTE_PATH)
    (root / "note.md").write_text("#public\n[[target]]\n")
    original = local.prepare_publication().pages[0]
    remote.pages = [remote.matching(original)]
    (root / "target.md").write_text("#public\nTarget")
    page = next(page for page in local.prepare_publication().pages if page.name == "note.html")
    assert page.action == "update" and page.source_hash == original.source_hash
    assert page.rendered_hash != original.rendered_hash


def test_images_compare_exact_bytes_and_explicit_refresh(local, remote):
    (Path(local.NOTE_PATH) / "note.md").write_text("#public\n![[photo.png]]")
    data = b"\x89PNG\r\n\x1a\nFirst"
    path = Path(local.IMG_PATH) / "photo.png"
    path.write_bytes(data)
    image, = local.prepare_publication().images
    remote.images = [{"name": "photo.png", "source_hash": image.source_hash, "etag": f'"sha256-{image.source_hash}"'}]
    assert local.prepare_publication().images[0].action == "unchanged"
    assert local.prepare_publication(refresh_images=True).images[0].action == "update"
    stamp = path.stat().st_mtime
    path.write_bytes(data + b"Changed")
    os.utime(path, (stamp, stamp))
    assert local.prepare_publication().images[0].action == "update"
    path.write_bytes(b"not a png")
    with pytest.raises(ValueError, match="valid images"):
        local.prepare_publication()


def test_preservation_pruning_legacy_and_semantic_collisions_are_explicit(local, remote):
    page = local.prepare_publication().pages[0]
    remote.pages = [remote.matching(page), {"pub_name": "legacy.html", "etag": None}]
    assert local.prepare_publication().pages[-1].action == "preserve"
    assert local.prepare_publication(prune=True).pages[-1].action == "conflict"
    remote.pages[-1] = remote.matching(page) | {"pub_name": "extra.html"}
    assert local.prepare_publication(prune=True).pages[-1].action == "delete"
    remote.routes = {"valid": False, "conflicts": [{"name": "note", "detail": "collision"}]}
    assert local.prepare_publication().pages[0].action == "conflict"
    remote.routes = {"valid": True, "conflicts": []}
    remote.pages = [{"pub_name": "note.html", "etag": None}]
    assert local.prepare_publication().pages[0].action == "conflict"


def test_only_a_capabilities_404_allows_automatic_legacy_fallback(local, remote):
    remote.status = 404
    assert local.prepare_publication(mode="auto") is None
    assert local.publication_plan()["mode"] == "legacy-0.9"
    with pytest.raises(requests.HTTPError):
        local.prepare_publication(mode="checked")
    for status in (403, 500):
        remote.status = status
        with pytest.raises(requests.HTTPError):
            local.publication_plan()
    remote.calls.clear()
    assert local.prepare_publication(mode="legacy") is None and remote.calls == []


@pytest.mark.parametrize("value", [None, {}, {"protocol": "revision-2"}])
def test_malformed_capabilities_never_downgrade(local, remote, value):
    remote.capabilities = value
    with pytest.raises(ValueError, match="contract"):
        local.prepare_publication()


@pytest.mark.parametrize("change", [
    {"etag": 'W/"weak"'}, {"source_hash": "invalid"}, {"rendered_hash": None},
    {"revision": True}, {"id": "bad"}, {"notebook_id": "bad"}, {"aliases": ["/api"]},
    {"pub_name": "../escape.html"},
])
def test_untrusted_inventory_records_fail_before_mutation(local, remote, change):
    page = local.prepare_publication().pages[0]
    remote.pages = [remote.matching(page) | change]
    with pytest.raises(ValueError):
        local.prepare_publication()


def test_duplicate_and_invalid_image_records_fail_closed(local, remote):
    page = local.prepare_publication().pages[0]
    remote.pages = [remote.matching(page)] * 2
    with pytest.raises(ValueError, match="Duplicate"):
        local.prepare_publication()
    remote.pages = []
    remote.images = [{"name": "photo.png", "source_hash": "0" * 64, "etag": '"mismatch"'}]
    with pytest.raises(ValueError, match="Image ETag"):
        local.prepare_publication()


def test_changes_during_rendering_invalidate_the_snapshot(local, remote, monkeypatch):
    original = local.convert_to_html
    def edit_during_render(note):
        content = original(note)
        (Path(local.NOTE_PATH) / "note.md").write_text("#public\nExternal edit")
        return content
    monkeypatch.setattr(local, "convert_to_html", edit_during_render)
    with pytest.raises(ValueError, match="source changed"):
        local.prepare_publication()


def test_pending_edits_bad_targets_and_limits_are_redacted_and_fail_early(local, remote):
    local.notes["note"].md_out = "Unsaved"
    with pytest.raises(RuntimeError, match="unsaved"):
        local.prepare_publication()
    assert remote.calls == []
    local.notes["note"].md_out = None
    local.API_BASE = "https://user:private-password@publish.example"
    with pytest.raises(ValueError) as error:
        local.prepare_publication()
    assert "private-password" not in str(error.value) and remote.calls == []
    local.API_BASE = "https://publish.example"
    for limit in (0, 201, True):
        with pytest.raises(ValueError, match="limit"):
            local.publication_plan(limit=limit)
    with pytest.raises(ValueError, match="mode"):
        local.prepare_publication(mode="unsupported")


def test_json_preview_is_bounded(local, remote):
    (Path(local.NOTE_PATH) / "second.md").write_text("#public\nSecond")
    preview = local.publication_plan(limit=1)
    assert len(preview["pages"]) == 1 and preview["page_count"] == 2 and preview["truncated"]
