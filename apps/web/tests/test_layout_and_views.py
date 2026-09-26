import json
import sqlite3
from contextlib import closing

import pytest
from api import layout_api
from fastapi.testclient import TestClient
from main import create_app
from views import forms


def test_layout_update_persists_complete_settings(
    client,
    auth_headers,
    layout_payload,
    web_storage,
):
    layout_payload.update(
        {
            "NAV_BRAND": "Outside Labs",
            "NAV_PAGES": {"notes": "/notes"},
            "TITLE": "Pretty Notebook",
            "darkmode": True,
        }
    )

    response = client.post(
        "/api/layout",
        headers=auth_headers,
        json=layout_payload,
    )

    assert response.status_code == 201
    assert response.json() == layout_payload
    assert (
        json.loads(web_storage.settings.read_text(encoding="utf-8")) == layout_payload
    )


@pytest.mark.parametrize("missing_field", ["NAV_BRAND", "NAV_PAGES", "darkmode"])
def test_layout_update_rejects_incomplete_payload(
    client,
    auth_headers,
    layout_payload,
    missing_field,
):
    del layout_payload[missing_field]

    response = client.post(
        "/api/layout",
        headers=auth_headers,
        json=layout_payload,
    )

    assert response.status_code == 422


def test_layout_storage_failure_returns_server_error(
    client,
    auth_headers,
    layout_payload,
    monkeypatch,
):
    async def fail_update(*args, **kwargs):
        raise OSError("simulated settings failure")

    monkeypatch.setattr(layout_api, "update_layout", fail_update)
    response = client.post(
        "/api/layout",
        headers=auth_headers,
        json=layout_payload,
    )

    assert response.status_code == 500


def test_public_home_and_contact_pages_do_not_require_authentication(client):
    home = client.get("/")
    contact = client.get("/contact")

    assert home.status_code == 200
    assert "Test notebook" in home.text
    assert "Pretty Notebook" in home.text
    assert contact.status_code == 200
    assert "Contact" in contact.text
    assert 'action="/forms/contact"' in contact.text


def test_contact_form_saves_to_local_inbox(web_storage, tmp_path):
    database = tmp_path / "web.sqlite3"
    app = create_app(db_url=f"sqlite://{database}")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/forms/contact",
            data={"email_address": "person@example.com", "email_message": "Hello"},
            follow_redirects=False,
        )
        confirmation = client.get(response.headers["location"])

    assert response.status_code == 303
    assert response.headers["location"] == "/contact?sent=1"
    assert "Your message was saved locally" in confirmation.text
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute(
            "SELECT form_name, payload FROM formsubmission"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "contact"
    assert json.loads(rows[0][1]) == {
        "email_address": "person@example.com",
        "email_message": "Hello",
    }


@pytest.mark.parametrize(
    "data",
    [
        {"email_address": "bad", "email_message": "Hello"},
        {"email_address": "person@example.com", "email_message": "   "},
    ],
)
def test_contact_form_rejects_invalid_input(client, data):
    response = client.post("/forms/contact", data=data)

    assert response.status_code == 422
    assert "role=\"alert\"" in response.text


def test_contact_form_does_not_claim_success_on_storage_failure(client, monkeypatch):
    async def fail_save(*args, **kwargs):
        raise OSError("simulated inbox failure")

    monkeypatch.setattr(forms, "save_submission", fail_save)
    response = client.post(
        "/forms/contact",
        data={"email_address": "person@example.com", "email_message": "Hello"},
        follow_redirects=False,
    )

    assert response.status_code == 500


def test_unknown_form_returns_404(client):
    response = client.post("/forms/unknown", data={})

    assert response.status_code == 404


def test_saved_submissions_require_authentication_and_support_pagination(
    client, auth_headers
):
    for message in ("First", "Second"):
        saved = client.post(
            "/forms/contact",
            data={"email_address": "person@example.com", "email_message": message},
            follow_redirects=False,
        )
        assert saved.status_code == 303

    unauthenticated = client.get("/api/forms/contact/submissions")
    latest = client.get(
        "/api/forms/contact/submissions?limit=1&offset=0", headers=auth_headers
    )
    older = client.get(
        "/api/forms/contact/submissions?limit=1&offset=1", headers=auth_headers
    )

    assert unauthenticated.status_code == 401
    assert latest.status_code == older.status_code == 200
    assert latest.json()[0]["payload"]["email_message"] == "Second"
    assert older.json()[0]["payload"]["email_message"] == "First"
    assert latest.json()[0]["created_at"]


def test_inbox_rejects_invalid_page_size(client, auth_headers):
    response = client.get(
        "/api/forms/contact/submissions?limit=101", headers=auth_headers
    )

    assert response.status_code == 422


def test_published_page_is_publicly_readable(
    client,
    auth_headers,
):
    created = client.post(
        "/api/publishment",
        headers=auth_headers,
        json={"name": "public-note", "content": "<h1>Public note</h1>"},
    )
    page = client.get("/public-note")

    assert created.status_code == 201
    assert page.status_code == 200
    assert "<h1>Public note</h1>" in page.text


def test_missing_public_page_renders_custom_404_with_404_status(client):
    response = client.get("/missing-page")

    assert response.status_code == 404
    assert "Page doesn't exist" in response.text
    assert "missing-page" in response.text


def test_unknown_api_route_uses_json_404_not_public_page(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_missing_favicon_returns_404(client):
    response = client.get("/favicon.ico", follow_redirects=False)

    assert response.status_code == 404


@pytest.mark.parametrize("value", ["<script>alert(1)</script>", "true", "0"])
def test_invalid_theme_cookie_cannot_replace_layout_data(client, value):
    client.cookies.set("darkmode", value)

    response = client.get("/")

    assert response.status_code == 200
    assert "background-color: black" not in response.text
    if value.startswith("<"):
        assert value not in response.text


@pytest.mark.parametrize(
    ("mode", "expected_cookie", "dark_style_present"),
    [
        ("darkmode", "True", True),
        ("lightmode", "False", False),
    ],
)
def test_theme_form_sets_cookie_and_redirects_to_same_page(
    client,
    mode,
    expected_cookie,
    dark_style_present,
):
    response = client.post(
        "/theme",
        data={"darkmode": mode, "return_to": "/contact"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/contact"
    assert response.cookies["darkmode"] == expected_cookie

    page = client.get("/contact")
    assert ("background-color: black" in page.text) is dark_style_present


@pytest.mark.parametrize("return_to", ["https://evil.example", "//evil.example", "/\\evil.example"])
def test_theme_rejects_external_redirects(client, return_to):
    response = client.post(
        "/theme",
        data={"darkmode": "darkmode", "return_to": return_to},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "darkmode" not in response.cookies


def test_theme_rejects_unknown_mode(client):
    response = client.post("/theme", data={"darkmode": "custom"})

    assert response.status_code == 422
