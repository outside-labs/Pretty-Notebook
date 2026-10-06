import json
from functools import partial

import pytest
from fastapi.testclient import TestClient

from api import public_index
from api.public_index import PublicDocument, PublicHeading
from api.public_navigation import PublicNavigation
from main import create_app


def publish(client, name, body, **kwargs):
    client.portal.call(partial(client.app.state.publications.publish, name, body, **kwargs))


def page_report(client, route, **params):
    response = client.get(route, params=params)
    assert response.status_code == 200, response.text
    return response.context["navigation"]


def test_home_and_directory_indexes_are_current_escaped_and_paginated(client, web_storage):
    publish(client, "guides/a", "<p>A</p>", title="A <guide> & café")
    publish(client, "z-last", "<p>Z</p>", title="Last")
    publish(client, "private/hidden", "Hidden body", title="Private title")
    client.portal.call(partial(client.app.state.publications.delete, "private/hidden"))
    (web_storage.pages / "stale.html").write_text("Stale title")
    home = client.get("/")
    assert home.status_code == 200 and "Test notebook" in home.text and "Test footer" in home.text
    assert 'href="/n?directory=guides"' in home.text and 'href="/z-last"' in home.text
    assert "Private title" not in home.text and "Stale title" not in home.text
    first = client.get("/n", params={"limit": 1})
    second = client.get("/n", params={"limit": 1, "offset": 1})
    assert first.context["notebook_index"]["total"] == second.context["notebook_index"]["total"] == 2
    assert first.context["notebook_index"]["items"][0]["kind"] == "directory"
    assert second.context["notebook_index"]["items"][0]["route"] == "/z-last"
    assert "Next entries" in first.text and "Previous entries" in second.text
    directory = client.get("/n", params={"directory": "guides"})
    assert "A &lt;guide&gt; &amp; café" in directory.text
    assert directory.context["notebook_index"]["breadcrumbs"][-1]["url"] == "/n?directory=guides"
    assert "No published entries" in client.get("/n", params={"directory": "empty"}).text
    assert "No published entries" in client.get("/n", params={"offset": 100}).text


@pytest.mark.parametrize("params", [
    {"directory": "../hidden"}, {"directory": "/absolute"}, {"directory": "a//b"},
    {"directory": "a\\b"}, {"directory": "A"}, {"directory": "two words"},
    {"directory": "%2e%2e"}, {"directory": "a" * 500}, {"directory": "a?next=secret"},
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"offset": 10001},
])
def test_directory_params_are_bounded_and_reject_escapes(client, params):
    assert client.get("/n", params=params).status_code == 422


def test_outline_uses_visible_heading_text_and_quoted_existing_ids(client):
    body = ('<h1 id="intro">Hello <em>world</em></h1>'
            '<h2 id="café&amp;&quot;">Café &lt;label&gt;</h2>'
            '<h2 id="intro">Duplicate anchor</h2><h3>No anchor</h3>'
            '<h3 id="bad id">Invalid anchor</h3><h4></h4>'
            '<script>secret</script><style>hidden style</style>'
            '<template><h2 id="secret">Private outline</h2></template>'
            '<pre>&lt;h2 id="literal"&gt;Code&lt;/h2&gt;</pre>')
    publish(client, "guides/page", body, title="Page <title>")
    response = client.get("/guides/page")
    headings = response.context["navigation"]["outline"]
    assert [heading["title"] for heading in headings] == ["Hello world", "Café <label>", "Duplicate anchor", "No anchor", "Invalid anchor"]
    assert headings[0]["url"] == "/guides/page#intro"
    assert headings[1]["url"] == "/guides/page#caf%C3%A9%26%22"
    assert all(heading["url"] is None for heading in headings[2:])
    assert 'href="/guides/page#caf%C3%A9%26%22">Café &lt;label&gt;' in response.text
    assert '<span>No anchor</span>' in response.text
    assert "Page &lt;title&gt;" in response.text
    assert 'href="/n?directory=guides" data-notebook-back' in response.text
    publish(client, "plain", "<p>No headings</p>")
    assert page_report(client, "/plain")["outline"] == []


def test_cycles_backlinks_aliases_and_renamed_neighbors_are_stable(client):
    publish(client, "a", '<p>#public #food <a href="/old-b#missing">B</a><a href="/old-b">Again</a><a href="#self">Self</a></p>', title="First")
    publish(client, "b", '<p>#public #food <a href="/a">A</a></p>', title="Second", aliases=["/old-b"])
    publish(client, "last", "<p>#public</p>", title="Last")
    report = page_report(client, "/a")
    assert report["previous"] is None and report["next"]["route"] == "/b"
    assert [link["route"] for link in report["backlinks"]] == ["/a", "/b"]
    assert [link["route"] for link in report["related"]] == ["/b"]
    assert report["related"][0]["linked_from"] and report["related"][0]["links_to"]
    assert report["related"][0]["shared_tags"] == ("food",)
    publish(client, "guides/moved", '<p>#public #food <a href="/a">A</a></p>', previous_name="b", title="Renamed")
    moved = page_report(client, "/a")
    assert moved["next"]["route"] == "/guides/moved"
    assert [link["route"] for link in moved["related"]] == ["/guides/moved"]
    assert moved["related"][0]["title"] == "Renamed"
    assert client.get("/old-b").url.path == "/guides/moved"
    assert page_report(client, "/last")["next"] is None
    assert page_report(client, "/a", related="false")["related"] == []


def test_unrelated_or_unsafe_links_never_create_navigation_targets(client):
    targets = ("javascript:alert(1)", "https://outside.example/b", "//outside.example/b", "/b?secret=1",
               "/%62", "/../b", "../b", "/b/", "/b\\extra", "/missing")
    publish(client, "a", "".join(f'<a href="{href}">Unsafe</a>' for href in targets))
    publish(client, "b", '<p>#public</p><template><a href="/a">Hidden</a></template><pre><a href="/a">Code</a></pre>')
    report = page_report(client, "/a")
    assert report["backlinks"] == report["related"] == []
    assert page_report(client, "/b")["related"] == []


def test_private_deleted_and_stale_revisions_never_enter_generated_panels(client, monkeypatch):
    publish(client, "a", '<h1 id="old">Old outline</h1><a href="/hidden">Hidden</a>')
    publish(client, "hidden", '<a href="/a">Public before revocation</a>', title="Private title")
    client.portal.call(partial(client.app.state.publications.delete, "hidden"))
    original = public_index._read_blob
    def eligible_only(root, digest):
        assert root == client.app.state.publications.blobs
        # The hidden title/body must be filtered before extraction.
        body = original(root, digest)
        assert "Public before revocation" not in body
        return body
    monkeypatch.setattr(public_index, "_read_blob", eligible_only)
    report = page_report(client, "/a")
    assert report["next"] is None and report["backlinks"] == report["related"] == []
    assert "Private title" not in json.dumps(report)
    publish(client, "a", "<p>Current with no heading or links</p>", title="Current")
    assert page_report(client, "/a")["outline"] == []
    client.portal.call(partial(client.app.state.publications.delete, "a"))
    assert client.get("/a").status_code == 404
    assert client.get("/n").context["notebook_index"]["total"] == 0


def test_prefixed_indexes_breadcrumbs_relationships_and_assets(web_storage):
    with TestClient(create_app(db_url="sqlite://:memory:", root_path="/notes")) as client:
        publish(client, "guides/a", '<h1 id="intro">Introduction</h1><a href="/notes/guides/b">B</a><a href="b">Relative B</a>', title="A")
        publish(client, "guides/b", '<a href="/notes/guides/a">A</a>', title="B")
        index = client.get("/notes/n", params={"directory": "guides"})
        assert 'href="/notes/guides/a"' in index.text and 'href="/notes/n"' in index.text
        response = client.get("/notes/guides/a")
        report = response.context["navigation"]
        assert report["breadcrumbs"][1]["url"] == "/notes/n?directory=guides"
        assert report["next"]["url"] == "/notes/guides/b"
        assert report["related"][0]["url"] == "/notes/guides/b"
        assert report["outline"][0]["url"] == "/notes/guides/a#intro"
        assert 'data-root-path="/notes"' in response.text
        assert 'src="/notes/static/js/notebook-navigation.js"' in response.text
        assert client.get("/notes/static/js/notebook-navigation.js").status_code == 200


def test_missing_headings_and_relationship_metadata_are_bounded(client):
    body = "".join(f'<h2 id="h{number}">Heading {number}</h2><a href="/target">Link</a>' for number in range(150))
    publish(client, "source", body)
    publish(client, "target", "Plain")
    assert len(page_report(client, "/source")["outline"]) == 100
    parser = public_index._VisibleText()
    parser.feed("".join(f'<a href="/a{number}">Link</a>' for number in range(250)) + '<h1 id="last">Unclosed')
    parser.close()
    assert len(parser.links) == 200
    assert parser.headings[-1] == PublicHeading(1, "Unclosed", "last")


def test_navigation_capacity_failures_are_explicit(client, monkeypatch):
    publish(client, "one", "<p>Body</p>")
    monkeypatch.setattr(public_index, "MAX_DOCUMENTS", 0)
    for path in ("/", "/n", "/one"):
        assert client.get(path).status_code == 503


def test_pure_navigation_validates_routes_filters_ambiguous_links_and_bounds_pages():
    documents = (
        PublicDocument("/a", "A", "", (), ("/alias",)),
        PublicDocument("/notes/a", "B", "", (), ("/alias",)),
    )
    navigation = PublicNavigation(documents, prefix="/notes")
    assert navigation.resolve_link("/a", "/alias") is None
    assert navigation.resolve_link("/a", "/notes/a") is None
    assert navigation.page("/absent") is None
    for href in (None, "", "x" * 2001, "http://[", "/a\n", "/a\\b"):
        assert navigation.resolve_link("/a", href) is None
    for limit, offset in ((True, 0), (0, 0), (101, 0), (10, True), (10, -1), (10, 10001)):
        with pytest.raises(ValueError, match="Index"):
            navigation.directory(limit=limit, offset=offset)
    with pytest.raises(ValueError, match="Duplicate"):
        PublicNavigation((documents[0], documents[0]))
    with pytest.raises(ValueError):
        PublicNavigation((PublicDocument("//outside", "Unsafe", "", (), ()),))
