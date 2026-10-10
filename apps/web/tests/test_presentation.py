import asyncio
import re
from pathlib import Path

import pytest
from api.layout_api import render_nav


def test_native_navigation_escapes_labels_and_preserves_prefixes():
    rendered = asyncio.run(render_nav({
        '<Home>': '/home?a=1&b=2',
        'More & links': [{'Child <one>': '/child'}, {'External': 'https://example.com/'}],
    }, '/notes'))
    assert '<details class="nav-group"><summary>More &amp; links</summary>' in rendered
    assert 'href="/notes/home?a=1&amp;b=2"' in rendered
    assert 'href="/notes/child"' in rendered
    assert '&lt;Home&gt;' in rendered and 'Child &lt;one&gt;' in rendered
    assert 'href="https://example.com/"' in rendered
    assert 'data-bs-' not in rendered and 'aria-current' not in rendered


@pytest.mark.parametrize('path', ['/', '/contact', '/missing'])
def test_shared_pages_have_landmarks_focus_target_and_local_layout(client, path):
    response = client.get(path)
    assert 'href="#main-content">Skip to content' in response.text
    assert '<main id="main-content"' in response.text
    assert 'tabindex="-1"' in response.text
    assert '<nav class="shell site-nav" aria-label="Main navigation"' in response.text
    assert '<footer class="site-footer">' in response.text
    assert '/static/css/site.css' in response.text
    assert '650px' not in response.text and 'bootstrap.bundle' not in response.text
    assert 'bootstrap.min.css' not in response.text and 'data-bs-' not in response.text
    assert 'Dark theme' in response.text
    assert client.get('/static/css/site.css').status_code == 200


def test_long_titles_and_owner_markup_are_kept_without_a_framework(client, auth_headers, layout_payload):
    layout_payload.update(TITLE='<long>' * 80, NAV_BRAND='<strong>Outside Labs</strong>',
                          FOOTER='<p>Owner footer</p>', NAV_PAGES={'Browse': [{'Contact': '/contact'}]})
    assert client.post('/api/layout', headers=auth_headers, json=layout_payload).status_code == 201
    page = client.get('/')
    assert '<h1>&lt;long&gt;' in page.text
    assert '<strong>Outside Labs</strong>' in page.text
    assert '<p>Owner footer</p>' in page.text
    assert '<details class="nav-group">' in page.text


def test_contact_errors_are_announced_and_linked_to_fields(client):
    response = client.post('/forms/contact', data={'email_address': 'invalid', 'email_message': ''})
    assert response.status_code == 422
    assert 'id="form-error" role="alert"' in response.text
    assert response.text.count('aria-describedby="form-error"') == 2
    assert '<label for="email_address">' in response.text
    assert '<label for="email_message">' in response.text


def luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    channels = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return sum(channel * weight for channel, weight in zip(channels, (0.2126, 0.7152, 0.0722)))


def test_theme_colors_have_readable_text_and_visible_control_boundaries():
    css = '\n'.join(path.read_text() for path in (Path(__file__).resolve().parents[1] / 'static/css/themes').glob('*.css'))
    themes = re.findall(r'(?:^:root|\[data-theme="dark"\])\s*\{([^}]+)', css, re.MULTILINE)
    assert len(themes) == 10
    for theme in themes:
        colors = dict(re.findall(r'(--[\w-]+):\s*(#[a-f0-9]{6})', theme))
        pairs = [('color-text', 'color-bg', 4.5), ('color-text', 'color-surface', 4.5), ('color-primary', 'color-surface', 4.5),
                 ('color-text-muted', 'color-bg', 4.5), ('color-on-primary', 'color-primary', 4.5),
                 ('color-error', 'color-error-surface', 4.5), ('color-border', 'color-bg', 3), ('color-focus', 'color-surface', 3)]
        for foreground, background, minimum in pairs:
            bright, dark = sorted([luminance(colors['--' + foreground]), luminance(colors['--' + background])], reverse=True)
            assert (bright + 0.05) / (dark + 0.05) >= minimum, (foreground, background)


def test_removed_layout_libraries_are_absent_from_reviewed_assets(client):
    assert not any(name.startswith('bootstrap-') for name in client.app.state.assets.entries)
    assert client.get('/static/vendor/bootstrap/5.0.0-beta2/bootstrap.min.css').status_code == 404
