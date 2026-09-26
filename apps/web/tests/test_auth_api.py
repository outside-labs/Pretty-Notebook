from datetime import UTC, datetime, timedelta

import jwt
import pytest
from api import auth_api


def token_payload(token: str) -> dict:
    return jwt.decode(token, options={"verify_signature": False})


def test_create_user_redacts_authentication_secrets(client, root_credentials):
    response = client.post("/api/users", json=root_credentials)

    assert response.status_code == 200
    assert response.json() == {"id": 1, "username": root_credentials["username"]}
    assert "password" not in response.text
    assert "tok_uuid" not in response.text


def test_valid_credentials_issue_bearer_token_and_identify_user(
    client,
    root_credentials,
    root_user,
):
    response = client.post(
        "/api/token",
        data={
            "username": root_credentials["username"],
            "password": root_credentials["password_hash"],
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    token = response.json()["access_token"]
    payload = token_payload(token)
    assert payload["sub"] == str(root_user["id"])
    assert payload["username"] == root_user["username"]
    assert isinstance(payload["tok_uuid"], str)
    assert payload["exp"] > payload["iat"]

    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api", headers=headers).json() == {
        "authenticated": True,
        "username": root_user["username"],
    }
    assert client.get("/api/users/me", headers=headers).json() == root_user


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("missing", "correct horse battery staple"),
        ("owner", "wrong password"),
    ],
)
def test_invalid_credentials_are_rejected(client, root_user, username, password):
    response = client.post(
        "/api/token",
        data={"username": username, "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        ("GET", "/api", {}),
        ("GET", "/api/users/me", {}),
        ("POST", "/api/users/me", {"json": {"password_hash": "new password"}}),
        ("POST", "/api/publishment", {"json": {"name": "note", "content": "body"}}),
        ("POST", "/api/image", {"files": {"file": ("image.png", b"image")}}),
        ("GET", "/api/publishments", {}),
        ("GET", "/api/images", {}),
        ("DELETE", "/api/publishment/note.html", {}),
        (
            "POST",
            "/api/layout",
            {
                "json": {
                    "NAV_BRAND": "Brand",
                    "NAV_PAGES": {},
                    "FOOTER": "Footer",
                    "TITLE": "Title",
                    "darkmode": False,
                    "hljs_light": "default",
                    "hljs_dark": "xt256",
                    "merm_light": "default",
                    "merm_dark": "dark",
                }
            },
        ),
    ],
)
def test_protected_routes_reject_missing_bearer_token(
    client,
    method,
    path,
    request_kwargs,
):
    response = client.request(method, path, **request_kwargs)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("token_factory", "expected_detail"),
    [
        (lambda payload: "not-a-jwt", "Could not validate credentials"),
        (
            lambda payload: jwt.encode(
                payload,
                "incorrect-secret-that-is-at-least-32-bytes",
                algorithm="HS256",
            ),
            "Could not validate credentials",
        ),
        (
            lambda payload: jwt.encode(
                {key: value for key, value in payload.items() if key != "exp"},
                auth_api.JWT_SECRET,
                algorithm=auth_api.JWT_ALGO,
            ),
            "Could not validate credentials",
        ),
        (
            lambda payload: jwt.encode(
                {
                    **payload,
                    "iat": datetime.now(UTC) - timedelta(minutes=2),
                    "exp": datetime.now(UTC) - timedelta(minutes=1),
                },
                auth_api.JWT_SECRET,
                algorithm=auth_api.JWT_ALGO,
            ),
            "Token expired",
        ),
        (
            lambda payload: jwt.encode(
                {**payload, "sub": "not-an-integer"},
                auth_api.JWT_SECRET,
                algorithm=auth_api.JWT_ALGO,
            ),
            "Could not validate credentials",
        ),
        (
            lambda payload: jwt.encode(
                {**payload, "sub": "999999"},
                auth_api.JWT_SECRET,
                algorithm=auth_api.JWT_ALGO,
            ),
            "Could not validate credentials",
        ),
        (
            lambda payload: jwt.encode(
                {**payload, "tok_uuid": 123},
                auth_api.JWT_SECRET,
                algorithm=auth_api.JWT_ALGO,
            ),
            "Could not validate credentials",
        ),
    ],
)
def test_invalid_tokens_are_rejected(
    client,
    auth_token,
    token_factory,
    expected_detail,
):
    token = token_factory(token_payload(auth_token))
    response = client.get("/api", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json() == {"detail": expected_detail}
    assert response.headers["www-authenticate"] == "Bearer"


def test_issuing_a_new_token_revokes_the_previous_token(
    client,
    root_credentials,
    auth_token,
):
    response = client.post(
        "/api/token",
        data={
            "username": root_credentials["username"],
            "password": root_credentials["password_hash"],
        },
    )
    new_token = response.json()["access_token"]

    old_response = client.get(
        "/api",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    new_response = client.get(
        "/api",
        headers={"Authorization": f"Bearer {new_token}"},
    )

    assert old_response.status_code == 401
    assert old_response.json() == {"detail": "Token revoked or superseded"}
    assert new_response.status_code == 200


def test_password_change_revokes_token_and_replaces_credentials(
    client,
    root_credentials,
    auth_token,
):
    old_headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        "/api/users/me",
        headers=old_headers,
        json={"password_hash": "new correct password"},
    )

    assert response.status_code == 200
    assert client.get("/api", headers=old_headers).status_code == 401
    assert (
        client.post(
            "/api/token",
            data={
                "username": root_credentials["username"],
                "password": root_credentials["password_hash"],
            },
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/token",
            data={
                "username": root_credentials["username"],
                "password": "new correct password",
            },
        ).status_code
        == 200
    )


def test_only_root_user_can_create_later_accounts(client, auth_headers):
    second_user = {"username": "writer", "password_hash": "writer password"}

    assert client.post("/api/users", json=second_user).status_code == 401
    response = client.post("/api/users", headers=auth_headers, json=second_user)
    assert response.status_code == 200

    writer_token = client.post(
        "/api/token",
        data={"username": "writer", "password": "writer password"},
    ).json()["access_token"]
    response = client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"username": "third", "password_hash": "third password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Not allowed."}


def test_duplicate_username_is_rejected_without_exposing_secrets(
    client,
    root_credentials,
    root_user,
    auth_headers,
):
    response = client.post(
        "/api/users",
        headers=auth_headers,
        json=root_credentials,
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "IntegrityError"
    assert root_credentials["password_hash"] not in response.text
    assert "tok_uuid" not in response.text


def test_database_failure_during_required_authentication_returns_server_error(
    client,
    auth_token,
    monkeypatch,
):
    async def fail_lookup(*args, **kwargs):
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(auth_api.User, "get_or_none", fail_lookup)
    response = client.get(
        "/api",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 500


def test_database_failure_during_optional_authentication_is_not_hidden(
    client,
    root_user,
    monkeypatch,
):
    async def fail_authentication(*args, **kwargs):
        raise RuntimeError("simulated authentication failure")

    monkeypatch.setattr(auth_api, "get_current_user", fail_authentication)
    response = client.post(
        "/api/users",
        headers={"Authorization": "Bearer token"},
        json={"username": "writer", "password_hash": "writer password"},
    )

    assert response.status_code == 500
