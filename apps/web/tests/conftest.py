import importlib
import json
import os
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.templating import Jinja2Templates

WEB_ROOT = Path(__file__).resolve().parents[1]
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

os.environ["JWT_SECRET"] = "test-only-jwt-secret-do-not-use-1234"
os.environ["JWT_ALGO"] = "HS256"

layout_api = importlib.import_module("api.layout_api")
publish_api = importlib.import_module("api.publish_api")
create_app = importlib.import_module("main").create_app
home = importlib.import_module("views.home")


DEFAULT_LAYOUT = {
    "NAV_BRAND": "Pretty Notebook",
    "NAV_PAGES": {"home": "/"},
    "FOOTER": "Test footer",
    "TITLE": "Test notebook",
    "darkmode": False,
    "hljs_light": "default",
    "hljs_dark": "xt256",
    "merm_light": "default",
    "merm_dark": "dark",
}


@pytest.fixture()
def web_storage(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    shutil.copytree(WEB_ROOT / "templates", templates)
    pages = templates / "pages"
    (pages / ".gitignore").unlink(missing_ok=True)
    images = tmp_path / "images"
    settings = tmp_path / "web-settings.json"
    images.mkdir()
    settings.write_text(json.dumps(DEFAULT_LAYOUT), encoding="utf-8")

    monkeypatch.setattr(publish_api, "PUB_PATH", pages)
    monkeypatch.setattr(publish_api, "IMG_PATH", images)
    monkeypatch.setattr(layout_api, "WEB_SETTINGS_PATH", settings)
    monkeypatch.setattr(home, "templates", Jinja2Templates(templates))

    return SimpleNamespace(pages=pages, images=images, settings=settings)


@pytest.fixture()
def client(web_storage):
    app = create_app(db_url="sqlite://:memory:")
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture()
def root_credentials():
    return {"username": "owner", "password_hash": "correct horse battery staple"}


@pytest.fixture()
def root_user(client, root_credentials):
    response = client.post("/api/users", json=root_credentials)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def auth_token(client, root_credentials, root_user):
    response = client.post(
        "/api/token",
        data={
            "username": root_credentials["username"],
            "password": root_credentials["password_hash"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture()
def layout_payload():
    return deepcopy(DEFAULT_LAYOUT)
