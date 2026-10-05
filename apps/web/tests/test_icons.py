import json


def test_theme_actions_use_named_buttons_and_decorative_svg(client):
    page = client.get('/contact')
    assert 'Dark theme' in page.text and '<svg' in page.text
    assert 'aria-hidden="true" focusable="false"' in page.text
    assert 'bootstrap-icons' not in page.text and 'class="bi ' not in page.text
    assert '.woff' not in page.text
    client.post('/theme', data={'darkmode': 'darkmode', 'return_to': '/contact'})
    assert 'Light theme' in client.get('/contact').text


def test_legacy_brand_and_publication_icons_display_without_rewriting_state(client, auth_headers, layout_payload, web_storage):
    layout_payload['NAV_BRAND'] = '<i class="bi bi-book-fill"></i>'
    assert client.post('/api/layout', headers=auth_headers, json=layout_payload).status_code == 201
    body = '<p>External <i class="bi bi-box-arrow-up-right" style="font-size:10px;"></i></p>'
    saved = client.post('/api/publishment', headers=auth_headers, json={'name': 'legacy-icons', 'content': body})
    assert saved.status_code == 201
    page = client.get('/legacy-icons')
    assert 'aria-label="Notebook"' in page.text
    assert 'icon-sm' in page.text and 'bi-box-arrow' not in page.text
    assert json.loads(web_storage.settings.read_text())['NAV_BRAND'] == layout_payload['NAV_BRAND']
    # Run the read on the application's database loop.
    assert client.portal.call(client.app.state.publications.read_page, 'legacy-icons')['body'] == body


def test_removed_icon_files_are_no_longer_served(client):
    assert not any(name.startswith('icons-') for name in client.app.state.assets.entries)
    for path in ('/static/css/bootstrap-icons.css', '/static/css/fonts/bootstrap-icons.woff2',
                 '/static/vendor/bootstrap-icons/1.5.0/bootstrap-icons.css',
                 '/static/vendor/bootstrap-icons/1.5.0/fonts/bootstrap-icons.woff'):
        assert client.get(path).status_code == 404
