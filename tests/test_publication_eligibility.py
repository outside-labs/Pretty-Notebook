import pytest

from pnbp import Notebook


@pytest.fixture
def publication_root(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	monkeypatch.setenv("HTML_PATH", str(tmp_path / "html"))
	(tmp_path / "html").mkdir()
	return tmp_path


def test_real_exclusion_tag_survives_longer_tag_in_code(publication_root) -> None:
	(publication_root / "private.md").write_text(
		"#public #private\n```text\n#privately\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()
	note = notebook.notes["private"]

	assert {str(tag) for tag in note.tags} == {"#public", "#private"}
	assert not notebook.is_publishable(note)


def test_tags_inside_protected_spans_do_not_control_publication(
	publication_root,
) -> None:
	(publication_root / "protected.md").write_text(
		"#public\n"
		"[[note#private]]\n"
		"[site](https://example.test/#private)\n"
		"https://example.test/#private\n"
		"```text\n#private\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()
	note = notebook.notes["protected"]

	assert {str(tag) for tag in note.tags} == {"#public"}
	assert notebook.is_publishable(note)


def test_longer_tag_is_not_the_exclusion_tag(publication_root) -> None:
	(publication_root / "public.md").write_text(
		"#public #privately\n",
		encoding="utf-8",
	)
	notebook = Notebook()
	note = notebook.notes["public"]

	assert {str(tag) for tag in note.tags} == {"#public", "#privately"}
	assert notebook.is_publishable(note)


def test_local_publication_uses_central_eligibility_predicate(
	publication_root,
) -> None:
	(publication_root / "public.md").write_text("#public\nVisible.\n", encoding="utf-8")
	(publication_root / "private.md").write_text(
		"#public #private\n```text\n#privately\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	notebook.write_commits_to_local_html()

	assert (publication_root / "html" / "public.html").is_file()
	assert not (publication_root / "html" / "private.html").exists()


def test_public_link_filter_uses_eligibility_and_preserves_images(
	publication_root,
) -> None:
	(publication_root / "public.md").write_text("#public\n", encoding="utf-8")
	(publication_root / "private.md").write_text(
		"#public #private\n",
		encoding="utf-8",
	)
	(publication_root / "source.md").write_text(
		"#public\n[[public]] [[private]] ![[image.png]]\n",
		encoding="utf-8",
	)
	notebook = Notebook()
	notebook.PUB_LNK_ONLY = True

	html = notebook.convert_to_html(notebook.notes["source"])

	assert "href='/public'" in html
	assert "href='/private'" not in html
	assert "<img" in html
	assert "image.png" in html
