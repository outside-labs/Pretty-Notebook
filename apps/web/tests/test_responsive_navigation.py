from html.parser import HTMLParser


class Navigation(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.panel = self.toggle = self.menu = None
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id') == 'site-navigation': self.panel = attrs
        if 'nav-toggle' in attrs.get('class', '').split(): self.toggle = attrs
        if tag == 'details' and attrs.get('class') == 'site-menu': self.menu = attrs


def test_navigation_uses_a_closed_native_menu_at_every_width(client):
    page = client.get('/')
    nav = Navigation(page.text)
    assert 'hidden' not in nav.panel
    assert 'hidden' not in nav.toggle
    assert 'open' not in nav.menu
    assert nav.toggle['aria-controls'] == 'site-navigation'
    assert 'href="/n/search"' in page.text
    assert 'data-nav-breakpoint' not in page.text
    assert '/static/icons/appearance.svg#menu' in page.text
    assert '/static/icons/appearance.svg#sun' in page.text
    assert '/static/js/site-navigation.js' in page.text


def test_icon_only_buttons_keep_names_and_accept_legacy_breakpoints(client, auth_headers, layout_payload):
    layout_payload['APPEARANCE'].update(button_labels=False, nav_breakpoint=768)
    layout_payload['NAV_PAGES'] = {'A very long navigation label that must wrap safely': '/contact'}
    assert client.post('/api/layout', json=layout_payload, headers=auth_headers).status_code == 201
    page = client.get('/')
    nav = Navigation(page.text)
    assert nav.toggle['aria-label'] == 'Menu'
    assert 'class="control-label visually-hidden"' in page.text
    assert 'aria-label="Dark theme"' in page.text
    assert 'open' not in nav.menu
    assert 'data-nav-breakpoint' not in page.text
    for bad in (0, 1441, True, '992px'):
        layout_payload['APPEARANCE']['nav_breakpoint'] = bad
        assert client.post('/api/layout', json=layout_payload, headers=auth_headers).status_code == 422
