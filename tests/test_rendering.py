import html
import re

import pytest

from pnbp import Notebook


@pytest.fixture
def notebook(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	(tmp_path / "other.md").write_text("Other.\n", encoding="utf-8")
	return tmp_path


def _code_fragments(rendered):
	return [
		html.unescape(fragment)
		for fragment in re.findall(r"<code[^>]*>(.*?)</code>", rendered, flags=re.DOTALL)
	]


def test_fenced_code_keeps_wikilinks_and_comments_literal(notebook):
	source = (
		"Normal [[other]].\n\n"
		"```text\n[[other]]\n```\n\n"
		"```python\n# comment\n```\n"
	)
	(notebook / "alpha.md").write_text(source, encoding="utf-8")
	nb = Notebook()

	rendered = nb.convert_to_html(nb.notes["alpha"])
	fragments = _code_fragments(rendered)

	assert rendered.count("href='/other'") == 1
	assert any("[[other]]" in fragment for fragment in fragments)
	assert any("# comment" in fragment for fragment in fragments)
	assert all("<a " not in fragment for fragment in fragments)
	assert all("id=\"comment\"" not in fragment for fragment in fragments)


def test_inline_and_plain_comparisons_are_not_highlights(notebook):
	(notebook / "alpha.md").write_text(
		"Inline `x == y == z` and plain x == y == z.\n",
		encoding="utf-8",
	)
	nb = Notebook()

	rendered = nb.convert_to_html(nb.notes["alpha"])

	assert "<code>x == y == z</code>" in rendered
	assert "plain x == y == z" in rendered
	assert "<mark>" not in rendered


def test_separate_formatting_spans_stay_separate(notebook):
	(notebook / "alpha.md").write_text(
		"~~one~~ and ~~two~~\n\n==three== and ==four==\n",
		encoding="utf-8",
	)
	nb = Notebook()

	rendered = nb.convert_to_html(nb.notes["alpha"])

	assert "<s>one</s> and <s>two</s>" in rendered
	assert "<mark>three</mark> and <mark>four</mark>" in rendered


def test_heading_ids_apply_only_to_headings(notebook):
	(notebook / "alpha.md").write_text(
		"# Real Heading\n\nParagraph with # comment text.\n",
		encoding="utf-8",
	)
	nb = Notebook()

	rendered = nb.convert_to_html(nb.notes["alpha"])

	assert '<h1 id="real-heading">Real Heading</h1>' in rendered
	assert "Paragraph with # comment text." in rendered
	assert 'id="comment-text"' not in rendered


def test_mermaid_rendering_and_pending_state_survive(notebook):
	(notebook / "alpha.md").write_text("Original.\n", encoding="utf-8")
	nb = Notebook()
	note = nb.notes["alpha"]
	note.md_out = "```mermaid\ngraph TD\nA --> B\n```\n"

	rendered = nb.convert_to_html(note)

	assert '<div class="mermaid">' in rendered
	assert "graph TD" in rendered
	assert note.md_out == "```mermaid\ngraph TD\nA --> B\n```\n"
