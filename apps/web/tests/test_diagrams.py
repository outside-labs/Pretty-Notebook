import hashlib

import pytest
from api import catalog


@pytest.fixture(autouse=True)
def asset_mode(monkeypatch, request):
    monkeypatch.setenv("PNBP_ASSET_MODE", getattr(request, "param", "local"))


def checked_page(client, auth_headers, name, body):
    response = client.put("/api/publishing/publication", headers={**auth_headers, "If-None-Match": "*"},
        json={"name": name, "content": body, "source_hash": "1" * 64,
              "rendered_hash": hashlib.sha256(body.encode()).hexdigest(), "renderer_fingerprint": "2" * 64})
    assert response.status_code == 201, response.text
    return response


def test_fixed_routes_and_known_plain_pages_have_no_diagram_loader(client, auth_headers):
    checked_page(client, auth_headers, "plain", "<p>Plain page</p><pre><code>Ordinary code</code></pre>")
    for path in ("/", "/contact", "/absent", "/plain"):
        response = client.get(path)
        assert "diagram-loader.js" not in response.text
        assert "mermaid.min.js" not in response.text
        assert "hljs.highlightAll" not in response.text
        assert ("code-tools.js" in response.text) is (path == "/plain")


@pytest.mark.parametrize("asset_mode", ["local", "cdn"], indirect=True)
def test_metadata_selects_the_reviewed_conditional_diagram_asset(client, auth_headers, asset_mode):
    checked_page(client, auth_headers, "diagram", '<pre class="mermaid">graph TD; A--&gt;B</pre>')
    response = client.get("/diagram")
    assert 'data-diagram-mode="required"' in response.text
    assert 'src="/static/js/diagram-loader.js"' in response.text
    resolver = client.app.state.assets
    if resolver.mode == "local":
        assert 'data-mermaid-src="http://testserver/static/vendor/mermaid/12.0.0/mermaid.min.js"' in response.text
    else:
        assert 'data-mermaid-src="https://cdn.jsdelivr.net/npm/mermaid@12.0.0/dist/mermaid.min.js"' in response.text
    assert 'data-mermaid-integrity="sha384-' in response.text
    assert '<script src="http://testserver/static/vendor/mermaid/' not in response.text
    assert client.get("/static/js/diagram-loader.js").status_code == 200


def test_legacy_pages_use_the_bounded_dom_fallback_and_language_fences_are_detected(client, auth_headers, web_storage):
    (web_storage.pages / "legacy.html").write_text('<pre><code class="language-mermaid">graph TD; A--&gt;B</code></pre>')
    assert 'data-diagram-mode="detect"' in client.get("/legacy").text
    checked_page(client, auth_headers, "language", '<pre><code class="language-mermaid">graph TD; A--&gt;B</code></pre>')
    assert 'data-diagram-mode="required"' in client.get("/language").text
    flags = catalog.feature_flags('<pre><code class="language-mermaid">graph TD</code></pre>')
    assert flags == ["code", "mermaid"]


def test_read_body_and_features_stay_bound_to_the_same_revision_during_a_write(client, auth_headers, monkeypatch):
    checked_page(client, auth_headers, "diagram", '<pre class="mermaid">graph TD; Original--&gt;Body</pre>')
    original = catalog._read_blob
    changed = False
    def update_during_read(directory, digest):
        nonlocal changed
        if not changed:
            changed = True
            response = client.post("/api/publishment", headers=auth_headers, json={"name": "diagram", "content": "New plain head"})
            assert response.status_code == 201
        return original(directory, digest)
    monkeypatch.setattr(catalog, "_read_blob", update_during_read)
    old = client.get("/diagram")
    assert "Original--&gt;Body" in old.text
    assert 'data-diagram-mode="required"' in old.text
    assert "New plain head" in client.get("/diagram").text
