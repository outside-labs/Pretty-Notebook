import hashlib

import pytest
from fastapi.testclient import TestClient
from main import create_app


def publish(client, headers, name, body):
    response = client.put('/api/publishing/publication', headers={**headers, 'If-None-Match': '*'},
        json={'name': name, 'content': body, 'source_hash': '1' * 64,
              'rendered_hash': hashlib.sha256(body.encode()).hexdigest(), 'renderer_fingerprint': '2' * 64})
    assert response.status_code == 201


def test_fixed_and_plain_pages_do_not_include_highlight_assets_or_code_tools(client, auth_headers):
    publish(client, auth_headers, 'plain', '<p>Plain text</p>')
    for path in ('/', '/contact', '/absent', '/plain'):
        page = client.get(path)
        assert 'highlight.min.js' not in page.text
        assert 'highlight.js/10.7.2/' not in page.text
        assert 'code-tools.js' not in page.text


@pytest.mark.parametrize('mode', ['local', 'cdn'])
def test_code_publications_pass_only_reviewed_conditional_assets(client, auth_headers, monkeypatch, mode):
    monkeypatch.setenv('PNBP_ASSET_MODE', mode)
    # Resolve the same reviewed assets under the selected policy.
    client.app.state.assets.mode = mode
    publish(client, auth_headers, 'code', '<pre><code class="language-python">  print(&quot;☃&quot;)\n</code></pre>')
    page = client.get('/code')
    assert 'src="/static/js/code-tools.js"' in page.text
    assert 'data-highlight="on"' in page.text
    assert 'data-highlight-integrity="sha384-' in page.text
    assert 'data-highlight-style-integrity="sha384-' in page.text
    assert ('data-highlight-src="http://testserver/static/vendor/' in page.text) is (mode == 'local')
    assert ('data-highlight-src="https://cdnjs.cloudflare.com/' in page.text) is (mode == 'cdn')
    assert '<script src="http://testserver/static/vendor/highlight' not in page.text
    assert '  print(&quot;☃&quot;)\n</code>' in page.text
    assert client.get('/static/js/code-tools.js').status_code == 200


def test_legacy_plain_and_code_pages_use_detection_without_global_highlighting(client, web_storage):
    (web_storage.pages / 'legacy.html').write_text('<p>No code</p>')
    page = client.get('/legacy')
    assert 'code-tools.js' in page.text
    assert 'highlightAll' not in page.text


def test_highlighting_can_be_disabled_without_hiding_source_or_copy_controls(web_storage, monkeypatch):
    monkeypatch.setenv('PNBP_CODE_HIGHLIGHT', 'off')
    (web_storage.pages / 'code.html').write_text('<pre><code class="language-python">print(1)\n</code></pre>')
    with TestClient(create_app(db_url='sqlite://:memory:')) as client:
        page = client.get('/code')
        assert 'data-highlight="off"' in page.text
        assert 'code-tools.js' in page.text
        assert '<pre><code class="language-python">print(1)\n</code></pre>' in page.text


def test_invalid_highlighting_policy_is_rejected(web_storage, monkeypatch):
    monkeypatch.setenv('PNBP_CODE_HIGHLIGHT', 'sometimes')
    with pytest.raises(RuntimeError, match='PNBP_CODE_HIGHLIGHT'):
        create_app(db_url='sqlite://:memory:')
