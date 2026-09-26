import json

import pytest
from api import layout_api


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
    assert "Email address" in contact.text


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
        "/",
        data={"darkmode": mode},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert response.cookies["darkmode"] == expected_cookie

    page = client.get("/")
    assert ("background-color: black" in page.text) is dark_style_present
