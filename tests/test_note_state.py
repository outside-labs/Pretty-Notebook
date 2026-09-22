import pytest

from pnbp.commands.correct import _collect_unlinked_mentions
from pnbp.commands.pprint import get_rich_note
from pnbp import Notebook


@pytest.fixture
def notebook(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	monkeypatch.setenv("HTML_PATH", str(tmp_path / "html"))
	(tmp_path / "alpha.md").write_text("A beta mention.\n", encoding="utf-8")
	(tmp_path / "beta.md").write_text("Beta body.\n", encoding="utf-8")
	return Notebook()


def test_collect_unlinked_mentions_preserves_note_state(notebook) -> None:
	original_state = {
		name: (note.md_out, note.pprotect.copy())
		for name, note in notebook.notes.items()
	}

	_collect_unlinked_mentions(nb=notebook)

	for name, state in original_state.items():
		assert (notebook.notes[name].md_out, notebook.notes[name].pprotect) == state


def test_collect_unlinked_mentions_rejects_pending_edits(notebook) -> None:
	note = notebook.notes["alpha"]
	note.md_out = "Pending edit.\n"

	with pytest.raises(RuntimeError, match="unsaved"):
		_collect_unlinked_mentions(nb=notebook)

	assert note.md_out == "Pending edit.\n"


def test_rich_note_rendering_preserves_pending_edit(notebook) -> None:
	note = notebook.notes["alpha"]
	note.md_out = "Pending [[beta]] edit.\n"

	get_rich_note(note=note, nb=notebook)

	assert note.md_out == "Pending [[beta]] edit.\n"
	assert note.is_unsaved


def test_reload_requires_explicit_discard_of_pending_edits(notebook) -> None:
	note = notebook.notes["alpha"]
	note.md_out = "Pending edit.\n"

	with pytest.raises(RuntimeError, match="unsaved"):
		notebook.open_md()

	assert notebook.notes["alpha"] is note
	assert note.md_out == "Pending edit.\n"

	notebook.open_md(discard_unsaved=True)

	assert notebook.notes["alpha"].md_out is None
	assert notebook.notes["alpha"].md == "A beta mention.\n"


def test_failed_reload_preserves_loaded_notes(notebook, monkeypatch) -> None:
	original_notes = notebook.notes

	def fail_to_open(*args, **kwargs):
		raise OSError("simulated read failure")

	monkeypatch.setattr(notebook, "open_note", fail_to_open)

	with pytest.raises(OSError, match="simulated read failure"):
		notebook.open_md()

	assert notebook.notes is original_notes


@pytest.mark.parametrize(
	"operation",
	[
		lambda nb: nb.write_commits_to_local_html(),
		lambda nb: nb.post_commits_to_web_api(stage_only=True),
	],
)
def test_publication_refuses_to_discard_pending_edits(notebook, operation) -> None:
	note = notebook.notes["alpha"]
	note.md_out = "Pending edit.\n"

	with pytest.raises(RuntimeError, match="unsaved"):
		operation(notebook)

	assert notebook.notes["alpha"] is note
	assert note.md_out == "Pending edit.\n"
