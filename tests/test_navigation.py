import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from pnbp import Notebook, NavigationHistory, NavigationIndex
from pnbp._navigation import Breadcrumb, DirectoryIndex, Heading, ReadingNeighbors


@pytest.fixture
def notebook(monkeypatch, tmp_path):
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	monkeypatch.delenv("NOTE_NESTED", raising=False)
	for directory in ("guides", "private", "empty"):
		(tmp_path / directory).mkdir()
	texts = {
		"a.md": "# Alpha\nTags: #public #food\n[[guides/b#Missing]] [[guides/b]] [[a]] [[private/hidden]]\n",
		"guides/b.md": "# Beta {#reading}\n## Repeat\n## Repeat\nTags: #public #food #work\n[[a]]\n",
		"guides/plain.md": "Tags: #public #work\nNo headings.\n",
		"private/hidden.md": "# Secret title\n#private\n[[a]]\n",
		"excluded.md": "#public #private [[a]]\n",
		"tail.md": "#public\n",
	}
	for name, text in texts.items():
		(tmp_path / name).write_text(text, encoding="utf-8")
	return Notebook(tmp_path, settings={"NOTE_NESTED": "recurs"})


def _files(notebook):
	root = Path(notebook.NOTE_PATH)
	return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_directory_indexes_breadcrumbs_are_derived_and_deterministic(notebook):
	before = _files(notebook)
	index = notebook.navigation_index()
	assert isinstance(index, NavigationIndex)
	root = index.directory()
	assert root.directories == ("guides", "private")
	assert [entry.name for entry in root.notes] == ["a", "excluded", "tail"]
	assert [entry.name for entry in index.directory("guides").notes] == ["guides/b", "guides/plain"]
	assert len(index.directory(recursive=True).notes) == len(notebook)
	assert index.directory("empty") == DirectoryIndex("empty", (), ())
	assert index.directory("unloaded") == DirectoryIndex("unloaded", (), ())
	assert index.breadcrumbs("guides/b") == (
		Breadcrumb("Notebook", ""), Breadcrumb("guides", "guides"), Breadcrumb("guides/b", "guides/b.md", True),
	)
	assert _files(notebook) == before
	assert not (Path(notebook.NOTE_PATH) / ".pnbp").exists()


def test_empty_notebook_has_a_known_empty_index(monkeypatch, tmp_path):
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	index = Notebook(tmp_path).navigation_index()
	assert index.entries == ()
	assert index.directory() == DirectoryIndex("", (), ())
	with pytest.raises(KeyError, match="not available"):
		index.neighbors("missing")


def test_outline_reuses_markdown_anchors_and_pending_text_without_saving(notebook):
	index = notebook.navigation_index()
	assert index.outline("guides/b") == (
		Heading(1, "Beta", "reading"), Heading(2, "Repeat", "repeat"), Heading(2, "Repeat", "repeat_1"),
	)
	assert index.outline("guides/plain") == ()
	note = notebook.notes["guides/b"]
	note.md_out = "Pending & **fresh**\n===================\n\n```md\n# Literal\n```\n"
	assert notebook.navigation_index().outline(note) == (Heading(1, "Pending & fresh", "pending-fresh"),)
	assert index.outline(note)[0].title == "Beta"
	assert note.md_out.startswith("Pending") and note.md.startswith("# Beta")


def test_cycles_backlinks_missing_headings_and_reading_neighbors(notebook):
	index = notebook.navigation_index()
	assert [entry.name for entry in index.backlinks("guides/b")] == ["a"]
	assert [entry.name for entry in index.backlinks("a")] == ["a", "excluded", "guides/b", "private/hidden"]
	assert index.neighbors("a").previous is None
	assert index.neighbors("tail").next is None
	assert index.neighbors("guides/b") == ReadingNeighbors(index.entry("excluded"), index.entry("guides/plain"))
	assert index.entry("guides/b#Missing").name == "guides/b"
	assert index.entry("[[guides/b|Label]]").name == "guides/b"
	assert index.entry("../a", source="guides/b.md").name == "a"
	with pytest.raises(KeyError, match="not available"):
		index.entry("missing")


def test_related_notes_explain_links_and_topic_tags_in_stable_order(notebook):
	index = notebook.navigation_index(public_only=True)
	results = index.related("a")
	assert [result.note.name for result in results] == ["guides/b"]
	assert results[0].linked_from and results[0].links_to
	assert results[0].shared_tags == ("#food",)
	assert [result.note.name for result in index.related("guides/b")] == ["a", "guides/plain"]
	assert index.related("tail") == ()
	assert len(index.related("guides/b", limit=1)) == 1


def test_public_projection_filters_titles_directories_and_relationships_before_reports(notebook):
	notebook.initialize_identities()
	notebook.notes["private/hidden"]._identity_record = replace(notebook.notes["private/hidden"].identity, title="Private metadata title")
	index = notebook.navigation_index(public_only=True)
	assert [entry.name for entry in index.entries] == ["a", "guides/b", "guides/plain", "tail"]
	assert index.directory().directories == ("guides",)
	assert [entry.name for entry in index.backlinks("a")] == ["a", "guides/b"]
	assert index.neighbors("a").next.name == "guides/b"
	assert index.neighbors("guides/plain").next.name == "tail"
	assert index.directory("private").notes == ()
	serialized = json.dumps([asdict(entry) for entry in index.entries])
	assert "Private metadata title" not in serialized and "private/hidden" not in serialized
	for target in ("private/hidden", "excluded", "missing"):
		with pytest.raises(KeyError, match="Note is not available"):
			index.entry(target)
	notebook.notes["a"].md_out = "#private Pending [[guides/plain]]"
	fresh = notebook.navigation_index(public_only=True)
	assert [entry.name for entry in fresh.entries] == ["guides/b", "guides/plain", "tail"]
	assert fresh.backlinks("guides/plain") == ()


def test_pending_relationships_and_titles_are_current(notebook):
	notebook.initialize_identities()
	notebook.notes["a"]._identity_record = replace(notebook.notes["a"].identity, title="A title")
	notebook.notes["a"].md_out = "#food [[guides/plain]]"
	index = notebook.navigation_index()
	assert index.entry("A title").name == "a"
	assert index.breadcrumbs("a")[-1].label == "A title"
	assert [entry.name for entry in index.backlinks("guides/plain")] == ["a"]
	assert index.backlinks("guides/b") == ()


def test_history_is_independent_opt_in_and_does_not_change_sources(notebook):
	before = _files(notebook)
	first, second = notebook.traversal(), notebook.traversal()
	assert isinstance(first, NavigationHistory)
	assert first.current is second.current is None
	assert first.back() is first.forward() is None
	notebook.get("a")
	notebook.search("food")
	notebook.navigation_index().outline("a")
	assert first.current is None
	first.visit("a")
	first.visit("guides/b")
	first.visit("guides/b")
	assert first.back().name == "a"
	assert first.back() is None and first.current.name == "a"
	assert first.forward().name == "guides/b"
	assert second.current is None
	assert _files(notebook) == before


def test_history_cycles_and_new_visits_clear_the_forward_trail(notebook):
	history = notebook.traversal()
	for target in ("a", "guides/b", "a"):
		history.visit(target)
	assert history.back().name == "guides/b"
	assert history.back().name == "a"
	assert history.forward().name == "guides/b"
	history.visit("tail")
	assert history.forward() is None
	assert history.back().name == "guides/b"
	assert history.back().name == "a"


def test_missing_entries_are_skipped_and_invalid_visits_preserve_history(notebook):
	history = notebook.traversal()
	for target in ("a", "guides/b", "tail"):
		history.visit(target)
	with pytest.raises(KeyError, match="not available"):
		history.visit("typo")
	assert history.current.name == "tail"
	(Path(notebook.NOTE_PATH) / "guides/b.md").unlink()
	notebook.reload()
	assert history.back().name == "a"
	assert history.forward().name == "tail"
	(Path(notebook.NOTE_PATH) / "tail.md").unlink()
	notebook.reload()
	assert history.current is None
	assert history.back().name == "a"
	assert history.forward() is None and history.current.name == "a"


def test_history_follows_uuid_through_managed_rename_and_move(notebook):
	notebook.initialize_identities()
	history = notebook.traversal()
	history.visit("a")
	visited = history.visit("guides/b")
	notebook.rename_note("guides/b", "Renamed")
	assert history.current.name == "guides/Renamed"
	assert history.current.note_id == visited.note_id
	assert history.back().name == "a"
	assert history.forward().name == "guides/Renamed"
	notebook.move_note("guides/Renamed", "elsewhere/Moved")
	assert history.current.name == "elsewhere/Moved"
	assert notebook.navigation_index().entry(f"id:{visited.note_id}").name == "elsewhere/Moved"


def test_identity_visit_does_not_adopt_a_replacement_note_at_the_old_path(notebook):
	notebook.initialize_identities()
	history = notebook.traversal()
	history.visit("a")
	notebook.rename_note("a", "Renamed")
	notebook.generate_note("a", "New note with a new identity")
	assert history.current.name == "Renamed"
	assert history.current.note_id != notebook.notes["a"].note_id


def test_path_history_does_not_guess_after_external_rename(notebook):
	history = notebook.traversal()
	history.visit("a")
	history.visit("guides/b")
	(Path(notebook.NOTE_PATH) / "guides/b.md").rename(Path(notebook.NOTE_PATH) / "guides/New.md")
	notebook.reload()
	assert history.current is None
	assert history.back().name == "a"
	assert history.forward() is None


def test_public_history_skips_notes_made_private_and_preserves_pending_text(notebook):
	history = notebook.traversal(public_only=True)
	for target in ("a", "guides/b", "tail"):
		history.visit(target)
	notebook.notes["guides/b"].md_out = "Pending #private"
	assert history.back().name == "a"
	assert history.forward().name == "tail"
	with pytest.raises(KeyError, match="not available"):
		history.visit("private/hidden")
	assert history.current.name == "tail"
	assert notebook.notes["guides/b"].md_out == "Pending #private"


def test_history_limit_bounds_cycles(notebook):
	history = notebook.traversal(limit=2)
	for target in ("a", "guides/b", "a", "tail"):
		history.visit(target)
	assert history.back().name == "a"
	assert history.back() is None
	assert history.forward().name == "tail"


@pytest.mark.parametrize("path", ["../escape", "/absolute", ".pnbp", "private/../guides", "a\\b", "a//b", 1])
def test_invalid_directory_paths_fail_without_writes(notebook, path):
	before = _files(notebook)
	with pytest.raises(ValueError, match="directory"):
		notebook.navigation_index().directory(path)
	assert _files(notebook) == before


@pytest.mark.parametrize("options", [{"public_only": 1}, {"public_only": "yes"}, {"limit": True}, {"limit": 0}, {"limit": 201}])
def test_invalid_history_options_fail_clearly(notebook, options):
	with pytest.raises(ValueError):
		notebook.traversal(**options)


def test_navigation_option_types_are_explicit(notebook):
	with pytest.raises(ValueError, match="boolean"):
		notebook.navigation_index(public_only="yes")
	with pytest.raises(ValueError, match="boolean"):
		notebook.navigation_index().directory(recursive=1)
	for limit in (True, 0, 51, 1.5):
		with pytest.raises(ValueError, match="limit"):
			notebook.navigation_index().related("a", limit=limit)
