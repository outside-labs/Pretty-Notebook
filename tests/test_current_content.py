import pytest

from pretty_notebook import Notebook


@pytest.fixture
def notebook(monkeypatch, tmp_path):
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	monkeypatch.delenv("NOTE_NESTED", raising=False)
	(tmp_path / "example.md").write_text("#old [[loaded]] https://loaded.example\n")
	return Notebook(tmp_path)


def test_current_components_refresh_without_changing_loaded_fields(notebook):
	note = notebook.notes["example"]
	loaded = note.current_content
	assert note.current_content is loaded
	note.md_out = "#new [[pending]] https://pending.example\n```py\nprint('new')\n```\n"
	assert tuple(map(str, note.current_tags)) == ("#new",)
	assert tuple(map(str, note.current_links)) == ("pending",)
	assert tuple(map(str, note.current_urls)) == ("https://pending.example",)
	assert note.current_codeblocks[0].body == "print('new')\n"
	assert list(map(str, note.tags)) == ["#old"]
	assert note.md == loaded.md
	note.discard_changes()
	assert note.current_content == loaded
	assert note.current_content is not loaded


def test_empty_pending_content_and_saved_note_instance(notebook):
	note = notebook.notes["example"]
	note.md_out = ""
	assert note.current_content.md == ""
	assert note.current_tags == note.current_links == ()
	saved = note.save(notebook)
	assert saved is notebook.notes["example"] and saved is not note
	assert saved.md == saved.current_md == ""
	assert saved.md_out is None
	assert note.md != saved.md


def test_rendering_uses_pending_links_and_preserves_source_state(notebook):
	notebook.PUB_LNK_ONLY = True
	note = notebook.notes["example"]
	note.md_out = "Pending [[missing]] #current"
	current = note.current_content
	html = notebook.convert_to_html(note)
	assert "href=" not in html
	assert "missing" in html
	assert note.md_out == "Pending [[missing]] #current"
	assert note.current_content == current


def test_search_uses_pending_content_and_reports_invalid_regex(notebook, capsys):
	note = notebook.notes["example"]
	note.md_out = "Literal [café] in pending content"
	hits = notebook.search("[café]")
	assert len(hits) == 1
	assert hits[0].name == "example"
	assert note.current_md[hits[0].start:hits[0].end] == "[café]"
	assert capsys.readouterr().out == ""
	with pytest.raises(ValueError, match="regular expression"):
		notebook.search("[", regex=True)
	assert note.md_out == "Literal [café] in pending content"


def test_invalid_pending_content_fails_clearly(notebook):
	with pytest.raises(TypeError, match="string or None"):
		notebook.notes["example"].md_out = 12


def test_generated_note_current_view_keeps_generated_marker_contract(notebook):
	note = notebook.generate_note("generated", "[[example]] #other", pnbp=True)
	assert tuple(map(str, note.current_tags)) == ("#pnbp",)
	assert note.current_links == note.current_urls == note.current_codeblocks == ()
