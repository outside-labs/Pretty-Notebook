import pytest

from pnbp import Notebook
from pnbp.commands.correct import (
	_collect_unlinked_mentions,
	_link_unlinked_mentions,
)


@pytest.fixture
def note_root(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	return tmp_path


def test_protected_components_round_trip_exactly(note_root) -> None:
	source = (
		"#start\n"
		"Text #tag [[ spaced link ]] [site](https://example.com/a?q=1) "
		"and https://outside.example/path.\n"
		"```python\n#inside [[code link]] https://code.example\n```\n"
	)
	(note_root / "alpha.md").write_text(source, encoding="utf-8")
	note = Notebook().notes["alpha"]

	note.prime_md_out_protect()

	assert note.md_out != source
	assert note.pprotect
	assert all(isinstance(value, str) for value in note.pprotect.values())

	note.prime_md_out_release()

	assert note.md_out == source
	assert note.pprotect == {}


def test_failed_protected_release_restores_skeleton(note_root) -> None:
	(note_root / "alpha.md").write_text("Text #tag.\n", encoding="utf-8")
	note = Notebook().notes["alpha"]
	note.prime_md_out_protect()
	skeleton = note.md_out
	key = next(iter(note.pprotect))
	note.pprotect[key] = object()

	with pytest.raises(TypeError):
		note.prime_md_out_release()

	assert note.md_out == skeleton
	assert key in note.pprotect


def test_protection_error_recommends_discard_operation(note_root) -> None:
	(note_root / "alpha.md").write_text("Text.\n", encoding="utf-8")
	note = Notebook().notes["alpha"]
	note.md_out = "Pending.\n"

	with pytest.raises(Exception, match="discard_changes"):
		note.prime_md_out_protect()


def test_link_mentions_handles_punctuation_name_at_document_edges(note_root) -> None:
	(note_root / "(.md").write_text("Punctuation note.\n", encoding="utf-8")
	(note_root / "alpha.md").write_text("( starts and ends (", encoding="utf-8")
	notebook = Notebook()

	_link_unlinked_mentions(note=notebook.notes["alpha"], nb=notebook)

	assert (note_root / "alpha.md").read_text(encoding="utf-8") == (
		"[[(]] starts and ends [[(]]"
	)


def test_link_mentions_matches_word_name_at_document_edges(note_root) -> None:
	(note_root / "beta.md").write_text("Target.\n", encoding="utf-8")
	(note_root / "alpha.md").write_text("beta starts\nand ends beta", encoding="utf-8")
	notebook = Notebook()

	_link_unlinked_mentions(note=notebook.notes["alpha"], nb=notebook)

	assert (note_root / "alpha.md").read_text(encoding="utf-8") == (
		"[[beta]] starts\nand ends [[beta]]"
	)


def test_link_mentions_preserves_existing_spaced_wikilink(note_root) -> None:
	(note_root / "beta.md").write_text("Target.\n", encoding="utf-8")
	(note_root / "alpha.md").write_text("[[ beta ]] and beta", encoding="utf-8")
	notebook = Notebook()

	_link_unlinked_mentions(note=notebook.notes["alpha"], nb=notebook)

	assert (note_root / "alpha.md").read_text(encoding="utf-8") == (
		"[[ beta ]] and [[beta]]"
	)


def test_link_mentions_cannot_match_inside_protection_marker(note_root) -> None:
	(note_root / "PNBPPROTECTED0.md").write_text("Target.\n", encoding="utf-8")
	(note_root / "alpha.md").write_text("#tag and PNBPPROTECTED0", encoding="utf-8")
	notebook = Notebook()

	_link_unlinked_mentions(note=notebook.notes["alpha"], nb=notebook)

	assert (note_root / "alpha.md").read_text(encoding="utf-8") == (
		"#tag and [[PNBPPROTECTED0]]"
	)


def test_collect_mentions_handles_punctuation_name(note_root) -> None:
	(note_root / "(.md").write_text("Punctuation note.\n", encoding="utf-8")
	(note_root / "alpha.md").write_text("A ( mention.\n", encoding="utf-8")
	notebook = Notebook()

	_collect_unlinked_mentions(nb=notebook)

	assert "all unlinked mentions" in notebook.notes
