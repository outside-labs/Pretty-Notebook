import json
import shutil
import socket
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from assets import AssetResolver
from fastapi.testclient import TestClient
from main import create_app

STATIC = Path(__file__).resolve().parents[1] / "static"


class RuntimeURLs(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.urls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and "src" in attrs:
            self.urls.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.urls.append(attrs["href"])


def copied_assets(tmp_path):
    root = tmp_path / "static"
    shutil.copytree(STATIC, root)
    return root


def test_local_page_and_all_runtime_assets_work_with_network_blocked(web_storage, monkeypatch):
    monkeypatch.setenv("PNBP_ASSET_MODE", "local")
    def blocked(*args, **kwargs):
        raise AssertionError("External networking is disabled")
    monkeypatch.setattr(socket, "create_connection", blocked)
    with TestClient(create_app(db_url="sqlite://:memory:")) as client:
        page = client.get("/")
        assert page.status_code == 200
        urls = RuntimeURLs(page.text).urls
        assert len(urls) == 6
        assert all(urlsplit(url).netloc == "testserver" for url in urls)
        for entry in client.app.state.assets.entries.values():
            asset = client.get("/static/" + entry["path"])
            assert asset.status_code == 200
            assert asset.headers["cache-control"] == "public, max-age=31536000, immutable"
            assert asset.headers["x-content-type-options"] == "nosniff"
        policy = page.headers["content-security-policy"]
        assert "object-src 'none'" in policy and "connect-src 'self'" in policy
        assert "cdn.jsdelivr.net" not in policy and "cdnjs.cloudflare.com" not in policy
        assert "immutable" not in client.get("/static/asset-manifest.json").headers.get("cache-control", "")


def test_explicit_cdn_mode_uses_only_pinned_integrity_checked_entries(web_storage, monkeypatch):
    monkeypatch.setenv("PNBP_ASSET_MODE", "cdn")
    with TestClient(create_app(db_url="sqlite://:memory:")) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert all(urlsplit(url).hostname in {"cdn.jsdelivr.net", "cdnjs.cloudflare.com"} for url in RuntimeURLs(page.text).urls)
        assert page.text.count('integrity="sha384-') == 6
        assert "https://cdn.jsdelivr.net" in page.headers["content-security-policy"]


def test_mixed_auto_mode_falls_back_as_a_dependency_group(tmp_path):
    root = copied_assets(tmp_path)
    original = AssetResolver(root, mode="local")
    original.path(original.entries["icons-woff2"]["path"]).unlink()
    resolver = AssetResolver(root, mode="auto")
    assert resolver.local("icons-css") is False
    assert resolver.local("bootstrap-js") is True
    request = type("Request", (), {"url_for": lambda self, *args, **kwargs: "/static/" + kwargs["path"]})()
    assert resolver.resolve("icons-css", request)["url"].startswith("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.5.0/")
    assert resolver.resolve("bootstrap-js", request)["local"] is True
    with pytest.raises(RuntimeError, match="Required local.*icons-woff2"):
        AssetResolver(root, mode="local")


def test_corrupt_or_symlink_asset_fails_closed_even_in_auto_mode(tmp_path):
    root = copied_assets(tmp_path)
    resolver = AssetResolver(root)
    path = resolver.path(resolver.entries["highlight-js"]["path"])
    original = path.read_bytes()
    path.write_bytes(original + b"tampered")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        AssetResolver(root)
    path.unlink()
    outside = tmp_path / "outside.js"
    outside.write_bytes(original)
    path.symlink_to(outside)
    with pytest.raises(RuntimeError, match="symlink"):
        AssetResolver(root, mode="cdn")


@pytest.mark.parametrize("change", ["path", "cdn", "version", "notice", "dependency", "schema"])
def test_invalid_asset_manifest_is_rejected(tmp_path, change):
    root = copied_assets(tmp_path)
    path = root / "asset-manifest.json"
    manifest = json.loads(path.read_text())
    entry = manifest["assets"]["bootstrap-css"]
    if change == "path":
        entry["path"] = "../outside.css"
    elif change == "cdn":
        entry["cdn"] = "https://untrusted.example/bootstrap.css"
    elif change == "version":
        entry["version"] = "unpinned"
    elif change == "notice":
        entry["notice"] = "missing-license"
    elif change == "dependency":
        entry["dependencies"] = ["unknown"]
    else:
        manifest["schema_version"] = 99
    path.write_text(json.dumps(manifest))
    with pytest.raises(RuntimeError):
        AssetResolver(root)


def test_layout_rejects_unreviewed_styles_before_storage(client, auth_headers, layout_payload, web_storage):
    before = web_storage.settings.read_bytes()
    layout_payload["hljs_light"] = "unreviewed"
    response = client.post("/api/layout", headers=auth_headers, json=layout_payload)
    assert response.status_code == 422
    assert web_storage.settings.read_bytes() == before
    with pytest.raises(ValueError, match="Unknown browser asset"):
        client.app.state.assets.resolve("unknown", None)


def test_invalid_mode_is_rejected():
    with pytest.raises(RuntimeError, match="PNBP_ASSET_MODE"):
        AssetResolver(STATIC, mode="unknown")


def test_deployment_installer_checks_without_network_and_verifies_download(tmp_path, monkeypatch):
    import install_assets
    root = copied_assets(tmp_path)
    entry = AssetResolver(root).entries["bootstrap-css"]
    path = root / entry["path"]
    original = path.read_bytes()
    path.unlink()
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def geturl(self):
            return entry["cdn"]
        def read(self, limit):
            return b"tampered"
    monkeypatch.setattr(install_assets, "urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(RuntimeError, match="checksum"):
        install_assets.install(root)
    assert not path.exists()
    monkeypatch.setattr(Response, "read", lambda self, limit: original)
    install_assets.install(root)
    assert path.read_bytes() == original
    assert list(path.parent.glob(".asset-*")) == []
