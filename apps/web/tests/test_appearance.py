import json

import pytest
import re


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


def test_preferences_page_has_example_controls_and_preview(client):
    page = client.get('/appearance')
    assert page.status_code == 200
    assert '<h1 id="appearance-title">Appearance preferences</h1>' in page.text
    form = re.search(r'<form[^>]*data-appearance-form>(.*?)</form>', page.text, re.DOTALL).group(1)
    def options(name):
        select = re.search(r'<select[^>]*name="' + name + r'"[^>]*>(.*?)</select>', form, re.DOTALL).group(1)
        return re.findall(r'<option[^>]*>([^<]+)</option>', select)
    assert options('theme') == ['Forest', 'Paper', 'Dark', 'Midnight']
    assert options('font') == ['Serif', 'Sans-serif', 'Monospace']
    assert options('density') == ['Comfortable', 'Compact']
    assert 'type="color" name="accent"' in page.text
    assert 'type="range" min="0" max="20" step="2"' in page.text
    for text in ['A warm reading surface', 'Blue-tinted dark mode', 'Soft botanical colors', 'Neutral charcoal',
                 'MY NOTEBOOK / WRITING', 'Every good idea begins somewhere.',
                 'A place to collect thoughts, stories, and discoveries.', 'New note', 'Edit notebook', 'Copy configuration']:
        assert text in page.text
    for palette in ['forest', 'paper', 'dark', 'midnight']:
        assert client.get(f'/static/css/themes/{palette}.css').status_code == 200
    assert 'href="/appearance"' in client.get('/').text


@pytest.mark.parametrize('theme,mode', [('forest', 'light'), ('paper', 'light'), ('dark', 'dark'), ('midnight', 'dark')])
def test_full_preferences_persist_across_pages_without_changing_owner_layout(client, web_storage, theme, mode):
    original = web_storage.settings.read_text()
    response = client.post('/appearance', data={'theme': theme, 'font': 'mono', 'density': 'compact',
                          'accent': '#ffee88', 'radius': 12, 'return_to': '/appearance?saved=1'}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/appearance?saved=1'
    assert response.cookies['appearance_mode'] == mode
    assert response.cookies['appearance_palette'] == theme
    for path in ('/', '/contact', '/appearance'):
        page = client.get(path)
        assert f'data-palette="{theme}"' in page.text
        assert f'data-theme="{mode}"' in page.text
        assert 'data-font="mono"' in page.text and 'data-density="compact"' in page.text
        assert '--radius-md:12px' in page.text
        assert '--color-primary:#ffee88' in page.text and '--color-on-primary:#000000' in page.text
    assert web_storage.settings.read_text() == original
    client.post('/appearance', data={'theme': theme, 'font': 'serif', 'accent': 'default'})
    assert '--color-primary:#ffee88' not in client.get('/').text


@pytest.mark.parametrize('values', [
    {'theme': '../escape'}, {'theme': 'outside'}, {'density': 'tiny'}, {'radius': 21}, {'radius': -1},
    {'radius': '1.5'}, {'accent': 'red;position:fixed'}, {'accent': '#abcdef;'},
])
def test_preference_form_rejects_untrusted_values_without_setting_cookies(client, values):
    response = client.post('/appearance', data={'theme': 'paper', 'font': 'serif', **values})
    assert response.status_code == 422
    assert not response.cookies


def test_invalid_preference_cookies_fall_back_to_owner_defaults(client):
    for key, value in [('palette', '../escape'), ('density', 'tiny'), ('accent', 'red;position:fixed'), ('radius', '999')]:
        client.cookies.set('appearance_' + key, value)
    page = client.get('/')
    assert 'data-palette="slate"' in page.text and 'data-density="comfortable"' in page.text
    assert '--radius-md:6px' in page.text and 'position:fixed' not in page.text
    client.cookies.set('appearance_radius', '-1')
    assert '--radius-md:6px' in client.get('/').text
    assert client.post('/appearance', data={'font': 'sans'}).status_code == 422
    assert client.post('/appearance', data={'theme': 'paper', 'font': 'sans', 'return_to': '//evil.test'}).status_code == 400
