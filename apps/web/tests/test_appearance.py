import json

import pytest


def test_legacy_layout_gets_defaults(client, web_storage):
    layout = json.loads(web_storage.settings.read_text())
    layout.pop('APPEARANCE')
    web_storage.settings.write_text(json.dumps(layout))
    page = client.get('/')
    assert page.status_code == 200
    assert '/static/css/themes/slate.css' in page.text
    assert 'data-font="sans"' in page.text


def test_appearance_survives_publication_and_reads(client, auth_headers, layout_payload, web_storage):
    layout_payload['APPEARANCE'].update(palette='outside', font='serif', density='compact',
                                      radius=10, header_bg='#212529')
    response = client.post('/api/layout', json=layout_payload, headers=auth_headers)
    assert response.status_code == 201
    assert json.loads(web_storage.settings.read_text())['APPEARANCE'] == layout_payload['APPEARANCE']
    page = client.get('/')
    assert '/static/css/themes/outside.css' in page.text
    assert 'data-font="serif"' in page.text and 'data-density="compact"' in page.text
    assert '--radius-md:10px' in page.text and '--nav-bg:#212529' in page.text
    assert client.get('/static/css/themes/outside.css').status_code == 200


@pytest.mark.parametrize('value', [{'palette': '../escape'}, {'accent': 'red;position:fixed'}, {'radius': -1}])
def test_api_rejects_unsafe_appearance(client, auth_headers, layout_payload, value):
    layout_payload['APPEARANCE'].update(value)
    assert client.post('/api/layout', json=layout_payload, headers=auth_headers).status_code == 422


def test_visitor_choices_persist_and_bad_values_do_not(client):
    response = client.post('/appearance', data={'mode': 'system', 'font': 'mono', 'return_to': '/contact'}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/contact'
    assert response.cookies['appearance_mode'] == 'system'
    assert response.cookies['appearance_font'] == 'mono'
    assert 'HttpOnly' in response.headers['set-cookie']
    page = client.get('/contact')
    assert 'data-mode="system"' in page.text and 'data-font="mono"' in page.text
    assert client.post('/appearance', data={'mode': 'invalid', 'font': 'mono'}).status_code == 422
    assert client.post('/appearance', data={'mode': 'dark', 'font': 'serif', 'return_to': '//evil.test'}).status_code == 400
    client.cookies.set('appearance_font', '../unsafe')
    assert 'data-font="sans"' in client.get('/').text


def test_custom_css_is_owner_controlled_persistent_and_loaded_last(client, auth_headers, layout_payload, web_storage):
    css = 'h1 { letter-spacing: .05em; }'
    assert client.put('/api/appearance/stylesheet', content=css).status_code == 401
    assert client.put('/api/appearance/stylesheet', content=css, headers=auth_headers).status_code == 204
    assert (web_storage.settings.parent / 'appearance.css').read_text() == css
    assert client.get('/static/custom/appearance.css').status_code == 404
    layout_payload['APPEARANCE']['custom_css'] = True
    assert client.post('/api/layout', json=layout_payload, headers=auth_headers).status_code == 201
    page = client.get('/')
    assert page.text.index('/static/custom/appearance.css') > page.text.index('/static/css/themes/')
    stylesheet = client.get('/static/custom/appearance.css')
    assert stylesheet.status_code == 200 and stylesheet.text == css
    assert stylesheet.headers['content-type'].startswith('text/css')
    assert client.put('/api/appearance/stylesheet', content='x' * 65_537, headers=auth_headers).status_code == 413
    assert client.put('/api/appearance/stylesheet', content=b'\xff', headers=auth_headers).status_code == 400
    assert (web_storage.settings.parent / 'appearance.css').read_text() == css
