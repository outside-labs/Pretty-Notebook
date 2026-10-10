from html.parser import HTMLParser


class Navigation(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.panel = self.toggle = None
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id') == 'site-navigation': self.panel = attrs
        if 'nav-toggle' in attrs.get('class', '').split(): self.toggle = attrs


def test_navigation_progressively_enhances_visible_links(client):
    page = client.get('/')
    nav = Navigation(page.text)
    assert 'hidden' not in nav.panel
    assert 'hidden' in nav.toggle
    assert nav.toggle['aria-controls'] == 'site-navigation'
    assert 'href="/n/search"' in page.text
    assert '(max-width: 992px)' in page.text
    assert '/static/js/site-navigation.js' in page.text


def test_icon_only_buttons_keep_names_and_custom_breakpoint(client, auth_headers, layout_payload):
    layout_payload['APPEARANCE'].update(button_labels=False, nav_breakpoint=768)
    layout_payload['NAV_PAGES'] = {'A very long navigation label that must wrap safely': '/contact'}
    assert client.post('/api/layout', json=layout_payload, headers=auth_headers).status_code == 201
    page = client.get('/')
    nav = Navigation(page.text)
    assert nav.toggle['aria-label'] == 'Menu'
    assert 'class="control-label visually-hidden"' in page.text
    assert 'aria-label="Dark theme"' in page.text
    assert '(max-width: 768px)' in page.text
    assert 'data-nav-breakpoint="768"' in page.text
    for bad in (0, 1441, True, '992px'):
        layout_payload['APPEARANCE']['nav_breakpoint'] = bad
        assert client.post('/api/layout', json=layout_payload, headers=auth_headers).status_code == 422
