from xml.etree import ElementTree

import pytest

from pretty_notebook import Notebook
from pretty_notebook._internal.icons import render_icon, replace_legacy_icons


@pytest.mark.parametrize('name', ['sun', 'moon', 'book', 'globe', 'external'])
def test_project_icons_are_inline_decorative_vectors(name):
    svg = ElementTree.fromstring(render_icon(name))
    assert svg.tag == '{http://www.w3.org/2000/svg}svg'
    assert svg.attrib['aria-hidden'] == 'true'
    assert svg.attrib['focusable'] == 'false'
    assert svg.attrib['viewBox'] == '0 0 24 24'
    assert len(svg) > 0


def test_named_icons_escape_accessible_labels_and_expose_size_style_controls():
    markup = render_icon('book', label='Notebook "<one>" & two', size='lg', variant='muted')
    svg = ElementTree.fromstring(markup)
    assert svg.attrib['aria-label'] == 'Notebook "<one>" & two'
    assert svg.attrib['role'] == 'img' and 'aria-hidden' not in svg.attrib
    assert svg.attrib['width'] == svg.attrib['height'] == '24'
    assert svg.attrib['class'] == 'icon icon-lg icon-muted'
    assert '<one>' not in markup


@pytest.mark.parametrize('options', [{'name': 'unknown'}, {'name': 'sun', 'size': 'giant'},
                                    {'name': 'sun', 'variant': 'onclick="bad()"'}])
def test_icons_reject_unknown_geometry_or_markup_controls(options):
    with pytest.raises(ValueError):
        render_icon(**options)


def test_legacy_icon_display_keeps_literal_code_and_unknown_markup():
    literal = '<pre><code><i class="bi bi-book-fill"></i></code><i class="bi bi-eye"></i></pre>'
    unknown = '<i class="bi bi-unknown"></i>'
    source = literal + unknown + '<i class="bi bi-globe2"></i>'
    rendered = replace_legacy_icons(source)
    assert literal in rendered and unknown in rendered
    assert 'aria-label="Published notebook"' in rendered
    assert rendered.count('<svg') == 1
    assert replace_legacy_icons(rendered) == rendered


def test_generated_external_links_use_svg_without_touching_literal_code(monkeypatch, tmp_path):
    monkeypatch.setenv('NOTE_PATH', str(tmp_path))
    monkeypatch.setenv('PNBP_SETTINGS', 'off')
    (tmp_path / 'note.md').write_text('[Example](https://example.com)\n\n```text\n[[note]] #tag\n```\n')
    notebook = Notebook()
    rendered = notebook.convert_to_html(notebook.notes['note'])
    assert 'href="https://example.com"' in rendered
    assert '<svg' in rendered and 'icon-sm' in rendered
    assert 'bi-box-arrow' not in rendered
    assert '[[note]] #tag' in rendered
