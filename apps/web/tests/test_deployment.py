"""Integration coverage for the supported persistent, single-process topology."""

import shutil
from stat import S_IMODE

from api import layout_api, publish_api
from fastapi.testclient import TestClient
from main import create_app, prepare_storage


def create_owner(client, credentials, bootstrap_headers):
    created = client.post(
        "/api/users",
        json=credentials,
        headers=bootstrap_headers,
    )
    assert created.status_code == 200
    token = client.post(
        "/api/token",
        data={
            "username": credentials["username"],
            "password": credentials["password_hash"],
        },
    )
    assert token.status_code == 200
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def populate_site(client, headers, layout_payload):
    layout_payload["TITLE"] = "Persistent site"
    assert client.post(
        "/api/layout",
        headers=headers,
        json=layout_payload,
    ).status_code == 201
    assert client.post(
        "/api/publishment",
        headers=headers,
        json={"name": "persistent-page", "content": "<h1>Still here</h1>"},
    ).status_code == 201
    assert client.post(
        "/api/image",
        headers=headers,
        files={"file": ("persistent.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
    ).status_code == 201
    assert client.post(
        "/forms/contact",
        data={"email_address": "person@example.com", "email_message": "Saved"},
        follow_redirects=False,
    ).status_code == 303


def assert_site_state(client, headers):
    assert client.get("/healthz").status_code == 200
    assert "Persistent site" in client.get("/").text
    assert "<h1>Still here</h1>" in client.get("/persistent-page").text
    assert client.get("/static/imgs/persistent.png").content == b"\x89PNG\r\n\x1a\nimage"
    inbox = client.get(
        "/api/forms/contact/submissions",
        headers=headers,
    )
    assert inbox.status_code == 200
    assert inbox.json()[0]["payload"]["email_message"] == "Saved"


def test_state_survives_clean_application_restart(
    tmp_path,
    web_storage,
    root_credentials,
    bootstrap_headers,
    layout_payload,
):
    database_url = f"sqlite://{tmp_path / 'site.db'}"

    with TestClient(create_app(db_url=database_url)) as client:
        headers = create_owner(client, root_credentials, bootstrap_headers)
        populate_site(client, headers, layout_payload)

    with TestClient(create_app(db_url=database_url)) as restarted:
        assert_site_state(restarted, headers)


def test_storage_initialization_creates_private_persistent_layout(
    tmp_path,
    monkeypatch,
):
    pages = tmp_path / "state" / "pages"
    images = tmp_path / "state" / "images"
    settings = tmp_path / "state" / "web-settings.json"
    monkeypatch.setattr(publish_api, "PUB_PATH", pages)
    monkeypatch.setattr(publish_api, "IMG_PATH", images)
    monkeypatch.setattr(layout_api, "WEB_SETTINGS_PATH", settings)

    prepare_storage()

    assert pages.is_dir()
    assert images.is_dir()
    assert settings.is_file()
    assert S_IMODE(settings.stat().st_mode) == 0o600


def test_health_check_fails_closed_when_settings_are_corrupt(client, web_storage):
    web_storage.settings.write_text("not json", encoding="utf-8")

    response = client.get("/healthz")

    assert response.status_code == 503
    assert response.json() == {"detail": "Persistent storage is unavailable."}


def test_stopped_site_backup_restores_all_persistent_state(
    tmp_path,
    web_storage,
    root_credentials,
    bootstrap_headers,
    layout_payload,
):
    database = tmp_path / "site.db"
    database_url = f"sqlite://{database}"

    with TestClient(create_app(db_url=database_url)) as client:
        headers = create_owner(client, root_credentials, bootstrap_headers)
        populate_site(client, headers, layout_payload)

    backup = tmp_path / "backup"
    backup.mkdir()
    shutil.copy2(database, backup / "site.db")
    shutil.copy2(web_storage.settings, backup / "web-settings.json")
    shutil.copytree(web_storage.pages, backup / "pages")
    shutil.copytree(web_storage.images, backup / "images")

    database.unlink()
    web_storage.settings.write_text("not json", encoding="utf-8")
    shutil.rmtree(web_storage.pages)
    shutil.rmtree(web_storage.images)

    shutil.copy2(backup / "site.db", database)
    shutil.copy2(backup / "web-settings.json", web_storage.settings)
    shutil.copytree(backup / "pages", web_storage.pages)
    shutil.copytree(backup / "images", web_storage.images)

    with TestClient(create_app(db_url=database_url)) as restored:
        assert_site_state(restored, headers)
