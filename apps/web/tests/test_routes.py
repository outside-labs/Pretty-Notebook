import json
from functools import partial

import pytest
from api import catalog
from fastapi.testclient import TestClient
from main import create_app
from tortoise import connections


def store_call(client, method, *args, **kwargs):
    return client.portal.call(partial(getattr(client.app.state.publications, method), *args, **kwargs))


def notes(client):
    async def query():
        return await connections.get("default").execute_query_dict("SELECT * FROM pnbp_notes ORDER BY canonical_route")
    return client.portal.call(query)


def test_nested_publication_alias_and_delete(client, auth_headers):
    response = client.post("/api/publishment", headers=auth_headers, json={"name": "python/functions", "content": "<h1 id='arguments'>Arguments</h1>", "title": "Function definitions", "aliases": ["/python-functions"]})
    assert response.status_code == 201
    assert "Arguments" in client.get("/python/functions").text
    alias = client.get("/python-functions", follow_redirects=False)
    assert alias.status_code == 308 and alias.headers["location"] == "/python/functions"
    assert notes(client)[0]["title"] == "Function definitions"
    assert client.delete("/api/publishment/python/functions.html", headers=auth_headers).status_code == 200
    assert client.get("/python/functions").status_code == client.get("/python-functions").status_code == 404


def test_explicit_migration_preserves_identity_revisions_and_legacy_file_on_restart(tmp_path, web_storage):
    database = tmp_path / "state.sqlite3"
    original = web_storage.pages / "python-functions.html"
    original.write_text("Original page")
    with TestClient(create_app(db_url=f"sqlite://{database}")) as client:
        original_id = notes(client)[0]["id"]
        store_call(client, "publish", "python/functions", "Migrated page", previous_name="python-functions", title="Function definitions")
        note, = notes(client)
        assert note["id"] == original_id and note["current_revision"] == 2
        assert json.loads(note["aliases"]) == ["/python-functions"]
    with TestClient(create_app(db_url=f"sqlite://{database}")) as restarted:
        note, = notes(restarted)
        assert note["id"] == original_id
        assert "Migrated page" in restarted.get("/python-functions").text
        assert len(store_call(restarted, "inventory")) == 1
    assert original.read_text() == "Original page"


def test_collision_preview_is_authenticated_read_only_and_checks_entire_plan(client, auth_headers, web_storage):
    store_call(client, "publish", "taken", "Original page")
    before = notes(client)
    claims = [{"name": "nested/new", "aliases": ["/taken"]}, {"name": "a", "aliases": ["/same"]}, {"name": "b", "aliases": ["/same"]}]
    assert client.post("/api/routes/preview", json=claims).status_code == 401
    preview = client.post("/api/routes/preview", headers=auth_headers, json=claims).json()
    assert preview["valid"] is False and len(preview["conflicts"]) == 2
    assert notes(client) == before
    assert len(list((web_storage.pages / ".blobs").glob("*.html"))) == 1
    collision = client.post("/api/publishment", headers=auth_headers, json={**claims[0], "content": "Never stored"})
    assert collision.status_code == 409
    assert len(list((web_storage.pages / ".blobs").glob("*.html"))) == 1


@pytest.mark.parametrize("claim", [{"name": "api/note"}, {"name": "appearance"}, {"name": "a%2fb"}, {"name": "n/books"}, {"name": "nested/next", "previous_name": "absent"}, {"name": "next", "aliases": ["/contact"]}])
def test_invalid_claim_preview_returns_actionable_conflict(client, auth_headers, claim):
    preview = client.post("/api/routes/preview", headers=auth_headers, json=[claim]).json()
    assert preview["valid"] is False and preview["conflicts"][0]["detail"]
    assert notes(client) == []


def test_existing_destination_and_alias_cannot_be_overwritten_by_migration(client):
    store_call(client, "publish", "old", "Old")
    store_call(client, "publish", "destination", "Other")
    with pytest.raises(catalog.RouteConflict, match="destination"):
        store_call(client, "publish", "destination", "Wrong", previous_name="old")
    store_call(client, "publish", "nested/new", "New", previous_name="old")
    with pytest.raises(catalog.RouteConflict):
        store_call(client, "publish", "old", "Wrong owner")
    assert "Other" in client.get("/destination").text


def test_uncataloged_alias_and_duplicate_migration_sources_fail_preview(client, web_storage):
    (web_storage.pages / "late.html").write_text("Late legacy page")
    preview = store_call(client, "preview_routes", [{"name": "nested/late", "aliases": ["/late"]}])
    assert preview["valid"] is False
    store_call(client, "publish", "old", "Original")
    preview = store_call(client, "preview_routes", [{"name": "one", "previous_name": "old"}, {"name": "two", "previous_name": "old"}])
    assert preview["valid"] is False


def test_failed_route_migration_keeps_old_route_and_head(client, monkeypatch):
    store_call(client, "publish", "old", "Original")
    original = catalog.PublicationStore._revision
    async def fail(self, transaction, *args):
        await original(self, transaction, *args)
        raise OSError("revision transaction failed")
    monkeypatch.setattr(catalog.PublicationStore, "_revision", fail)
    with pytest.raises(OSError):
        store_call(client, "publish", "nested/new", "New", previous_name="old")
    assert "Original" in client.get("/old").text
    assert client.get("/nested/new").status_code == 404


def test_prefix_deployment_routes_assets_navigation_forms_and_redirects(web_storage):
    with TestClient(create_app(db_url="sqlite://:memory:", root_path="/notes")) as client:
        store_call(client, "publish", "python/functions", "Functions", aliases=["/python-functions"])
        page = client.get("/notes/python/functions")
        assert page.status_code == 200
        for expected in ('href="/notes/"', 'action="/notes/theme"', '/notes/static/css/site.css'):
            assert expected in page.text
        assert client.get("/notes/healthz").headers["cache-control"] == "no-store"
        assert client.get("/notes/api/unknown").headers["cache-control"] == "no-store"
        asset = client.get("/notes/static/vendor/highlight.js/10.7.2/default.min.css")
        assert asset.status_code == 200 and "immutable" in asset.headers["cache-control"]
        alias = client.get("/notes/python-functions", follow_redirects=False)
        assert alias.headers["location"] == "/notes/python/functions"
        contact = client.get("/notes/contact")
        assert 'action="/notes/forms/contact"' in contact.text
        saved = client.post("/notes/forms/contact", data={"email_address": "person@example.com", "email_message": "Hello"}, follow_redirects=False)
        assert saved.headers["location"] == "/notes/contact?sent=1"
        theme = client.post("/notes/theme", data={"darkmode": "darkmode", "return_to": "/notes/python/functions"}, follow_redirects=False)
        assert theme.headers["location"] == "/notes/python/functions"
        assert "Path=/notes/" in theme.headers["set-cookie"]
        assert client.post("/notes/theme", data={"darkmode": "darkmode", "return_to": "/outside"}).status_code == 400
        preferences = client.get('/notes/appearance')
        assert preferences.status_code == 200
        assert 'action="/notes/appearance"' in preferences.text
        assert '/notes/static/js/appearance-preferences.js' in preferences.text
        saved_appearance = client.post('/notes/appearance', data={
            'theme': 'midnight', 'font': 'serif', 'radius': 10, 'density': 'compact',
            'accent': 'default', 'return_to': '/notes/appearance?saved=1'}, follow_redirects=False)
        assert saved_appearance.status_code == 303
        assert saved_appearance.headers['location'] == '/notes/appearance?saved=1'
        assert 'Path=/notes/' in saved_appearance.headers['set-cookie']
        assert 'data-palette="midnight"' in client.get('/notes/').text
        assert client.get("/notes/api/unknown").json() == {"detail": "Not Found"}


@pytest.mark.parametrize("path", ["/missing/nested", "/a%2fb", "/a%252fb", "/a%5cb", "/docs/note", "/static/no-such-file", "/n/books/missing"])
def test_unknown_and_encoded_routes_keep_real_404(client, path):
    assert client.get(path).status_code == 404
