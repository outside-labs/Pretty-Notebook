from functools import partial

import pytest
from api import catalog, public_index
from fastapi.testclient import TestClient
from main import create_app


def publish(client, name, body, **kwargs):
    client.portal.call(partial(client.app.state.publications.publish, name, body, **kwargs))


def search(client, q, **params):
    response = client.get("/api/search", params={"q": q, **params})
    assert response.status_code == 200, response.text
    return response.json()


def test_anonymous_literal_search_is_sorted_typed_and_paginated(client):
    for name in ("z-last", "nested/first", "a-first"):
        publish(client, name, "<p>Common punctuation: [a.b] and café Straße.</p>", title=name)
    first = search(client, "[a.b]", limit=2)
    second = search(client, "[a.b]", limit=2, offset=2)
    assert first["total"] == second["total"] == 3
    assert [hit["route"] for hit in first["hits"] + second["hits"]] == ["/a-first", "/nested/first", "/z-last"]
    assert first["hits"][0]["field"] == "content"
    assert first["hits"][0]["excerpt"].startswith("Common punctuation")
    assert search(client, ".*")["total"] == 0
    assert search(client, "CAFÉ")["total"] == search(client, "STRASSE")["total"] == 3
    assert search(client, "none")["hits"] == []
    assert search(client, "common", offset=10)["hits"] == []
    assert client.get("/api/search", params={"q": "common"}).headers["cache-control"] == "no-store"


def test_title_content_and_exact_tag_filters_use_visible_text(client):
    publish(client, "one", "<p>#public #Python Alpha<strong>beta</strong></p><pre><code>#literal</code></pre>"
            "<a href='/unknown'>#linked</a><script>secret<scripted</script>"
            "<style>private-style</style><template>private-template</template>", title="A <title>")
    publish(client, "two", "<p>#public #py Python Alpha body</p>", title="Second")
    assert search(client, "<title>", field="title")["hits"][0]["route"] == "/one"
    assert search(client, "Alphabeta", field="content")["total"] == 1
    assert search(client, "python", field="tag")["total"] == 1
    assert search(client, "alpha", tag=["#PUBLIC", "Python"])["total"] == 1
    assert search(client, "alpha", tag="py")["hits"][0]["route"] == "/two"
    for query in ("secret", "private-style", "private-template"):
        assert search(client, query)["total"] == 0
    for tag in ("literal", "linked"):
        assert search(client, "alpha", tag=tag)["total"] == 0
    assert search(client, "#literal", field="content")["total"] == 1


def test_current_revisions_replace_cache_and_never_expose_history_or_deleted_files(client, web_storage):
    publish(client, "one", "<p>Old unique body</p>", title="Old title", aliases=["/alias"])
    assert search(client, "Old")["total"] == 1
    before = client.app.state.public_index.documents
    assert search(client, "unique")["total"] == 1
    assert client.app.state.public_index.documents is before
    publish(client, "one", "<p>New unique body</p>", title="New title")
    assert search(client, "Old")["total"] == 0
    assert search(client, "New")["hits"][0]["title"] == "New title"
    publish(client, "nested/moved", "<p>Moved unique body</p>", previous_name="one", title="Moved title")
    assert search(client, "unique")["hits"][0]["route"] == "/nested/moved"
    assert search(client, "unique")["total"] == 1
    client.portal.call(partial(client.app.state.publications.delete, "nested/moved"))
    # An old legacy file and a complete unreferenced blob cannot re-enter search.
    (web_storage.pages / "one.html").write_text("Old unique legacy body")
    catalog._write_blob(client.app.state.publications.blobs, "Orphan unique body")
    assert search(client, "unique")["total"] == 0


def test_uncommitted_writes_never_enter_public_results(client, monkeypatch):
    publish(client, "one", "<p>Committed</p>")
    original = catalog.PublicationStore._revision
    async def fail(self, transaction, *args):
        await original(self, transaction, *args)
        raise OSError("interrupted transaction")
    monkeypatch.setattr(catalog.PublicationStore, "_revision", fail)
    with pytest.raises(OSError):
        publish(client, "one", "Uncommitted")
    assert search(client, "Committed")["total"] == 1
    assert search(client, "Uncommitted")["total"] == 0


def test_restart_rebuilds_derived_index_and_imports_only_stable_legacy_pages(tmp_path, web_storage):
    database = tmp_path / "state.sqlite3"
    (web_storage.pages / "legacy.html").write_text("<p>Legacy content</p>")
    with TestClient(create_app(db_url=f"sqlite://{database}")) as client:
        publish(client, "one", "<p>Durable content</p>", title="Durable")
        assert search(client, "content")["total"] == 2
        publish(client, "one", "<p>Replacement</p>", title="Durable")
    with TestClient(create_app(db_url=f"sqlite://{database}")) as restarted:
        assert search(restarted, "content")["hits"][0]["route"] == "/legacy"
        assert search(restarted, "replacement")["total"] == 1


def test_visibility_filter_precedes_snippets_counts_and_blob_reads(client, monkeypatch):
    publish(client, "deleted", "Never visible in the public index", title="Hidden title")
    client.portal.call(partial(client.app.state.publications.delete, "deleted"))
    def private_blob(*args):
        raise AssertionError("Ineligible body was read")
    monkeypatch.setattr(public_index, "_read_blob", private_blob)
    assert search(client, "Hidden")["total"] == 0


@pytest.mark.parametrize("params", [
    {}, {"q": ""}, {"q": " "}, {"q": "x" * 513}, {"q": "x", "field": "regex"},
    {"q": "x", "limit": 0}, {"q": "x", "limit": 101}, {"q": "x", "offset": -1},
    {"q": "x", "offset": 10001}, {"q": "x", "tag": "two-words"},
    {"q": "x", "tag": "x" * 65}, {"q": "x", "tag": ["one"] * 11},
    {"q": "x", "regex": "true"},
])
def test_public_query_language_is_bounded_and_literal(client, params):
    assert client.get("/api/search", params=params).status_code == 422


def test_search_page_escapes_queries_titles_and_excerpts_and_preserves_pagination(client):
    body = "<p>&lt;img src=x onerror=alert(1)&gt; &amp; safe</p>"
    for name in ("one", "two", "three"):
        publish(client, name, body, title="<script>title</script>")
    response = client.get("/n/search", params={"q": "<img", "field": "content", "limit": 1, "tag": []})
    assert response.status_code == 200
    assert '<form class="stack" method="get" action="/n/search" role="search">' in response.text
    assert "&lt;script&gt;title&lt;/script&gt;" in response.text
    assert "&lt;img src=x onerror=alert(1)&gt;" in response.text
    assert "<img src=x" not in response.text and "<script>title" not in response.text
    assert 'q=%3Cimg&amp;field=content&amp;limit=1&amp;offset=1' in response.text
    next_page = client.get("/n/search", params={"q": "<img", "limit": 1, "offset": 1})
    assert "Previous results" in next_page.text
    assert 'Search text is literal.' in client.get("/n/search").text
    assert client.get("/n/search", params={"q": " ", "tag": "bad-tag"}).status_code == 422


def test_prefixed_search_uses_canonical_prefixed_links_without_shadowing_notes(web_storage):
    with TestClient(create_app(db_url="sqlite://:memory:", root_path="/notes")) as client:
        publish(client, "nested/page", "<p>#public Prefixed</p>", title="Prefixed")
        publish(client, "search", "<p>Existing search-named publication</p>")
        assert "Existing search-named" in client.get("/notes/search").text
        response = client.get("/notes/n/search", params={"q": "Prefixed", "tag": "public"})
        assert response.status_code == 200
        assert 'action="/notes/n/search"' in response.text
        assert 'href="/notes/nested/page"' in response.text
        assert 'href="/notes/n/search"' in response.text
        assert 'name="tag" value="public"' in response.text


def test_optional_tag_input_is_empty_or_exact_and_initial_page_bounds_filters(client):
    publish(client, "one", "<p>#public #work searchable</p>")
    publish(client, "two", "<p>#public searchable</p>")
    assert search(client, "searchable", tag="")["total"] == 2
    response = client.get("/n/search", params={"q": "searchable", "tag": "work"})
    assert "1 matching page." in response.text
    assert 'id="tag-filter" name="tag" value="work"' in response.text
    assert client.get("/n/search", params={"tag": ["one"] * 11}).status_code == 422


def test_capacity_failures_are_explicit_and_corrupt_blobs_invalidate_cache(client, monkeypatch):
    publish(client, "one", "<p>One body</p>")
    assert search(client, "One")["total"] == 1
    with monkeypatch.context() as patch:
        patch.setattr(public_index, "MAX_DOCUMENTS", 0)
        assert client.get("/api/search", params={"q": "One"}).status_code == 503
    with monkeypatch.context() as patch:
        patch.setattr(public_index, "MAX_INDEX_BYTES", 1)
        client.app.state.public_index.signature = None
        assert client.get("/api/search", params={"q": "One"}).status_code == 503
    assert search(client, "One")["total"] == 1
    blob, = client.app.state.publications.blobs.iterdir()
    blob.write_text("Changed outside the catalog")
    assert client.get("/api/search", params={"q": "One"}).status_code == 500


def test_excerpt_handles_casefold_expansions_and_truncation(client):
    publish(client, "one", "<p>" + "before " * 50 + "Straße " + "after " * 50 + "</p>")
    excerpt = search(client, "STRASSE")["hits"][0]["excerpt"]
    assert excerpt.startswith("…") and excerpt.endswith("…")
    assert "Straße" in excerpt and len(excerpt) <= 202


def test_invalid_internal_query_types_fail_before_matching():
    for arguments in [("x", "any", 1, 20, 0), ("x", "any", [1], 20, 0),
                      ("x", "any", [], True, 0), ("x", "unknown", [], 20, 0)]:
        with pytest.raises(ValueError):
            public_index.validate_search(*arguments)
