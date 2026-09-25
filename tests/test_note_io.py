import os

import pytest

from pnbp import Notebook


@pytest.fixture
def note_root(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	return tmp_path


def test_generate_note_checks_nested_destination_on_disk(note_root) -> None:
	nested = note_root / "sub" / "old.md"
	nested.parent.mkdir()
	nested.write_text("Original.\n", encoding="utf-8")
	notebook = Notebook()

	with pytest.raises(FileExistsError):
		notebook.generate_note("sub/old", "Replacement.\n")

	assert nested.read_text(encoding="utf-8") == "Original.\n"


def test_generate_note_detects_uppercase_extension_collision(note_root) -> None:
	nested = note_root / "sub" / "old.MD"
	nested.parent.mkdir()
	nested.write_text("Original.\n", encoding="utf-8")
	notebook = Notebook()

	with pytest.raises(FileExistsError):
		notebook.generate_note("sub/old", "Replacement.\n")

	assert nested.read_text(encoding="utf-8") == "Original.\n"
	assert not (note_root / "sub" / "old.md").exists()


def test_generate_note_creates_and_returns_empty_note(note_root) -> None:
	notebook = Notebook()

	created = notebook.generate_note("_complete", "")

	assert created is notebook.notes["_complete"]
	assert (note_root / "_complete.md").is_file()
	assert (note_root / "_complete.md").read_text(encoding="utf-8") == ""


def test_generate_note_uses_exclusive_creation(note_root, monkeypatch) -> None:
	notebook = Notebook()
	destination = note_root / "raced.md"
	real_open = os.open

	def race_open(path, flags, mode=0o777):
		destination.write_text("Created elsewhere.\n", encoding="utf-8")
		return real_open(path, flags, mode)

	monkeypatch.setattr("pnbp.models.note.os.open", race_open)

	with pytest.raises(FileExistsError):
		notebook.generate_note("raced", "Our content.\n")

	assert destination.read_text(encoding="utf-8") == "Created elsewhere.\n"
	assert "raced" not in notebook.notes


def test_save_uses_atomic_replacement(note_root, monkeypatch) -> None:
	path = note_root / "alpha.md"
	path.write_text("Original.\n", encoding="utf-8")
	notebook = Notebook()
	note = notebook.notes["alpha"]
	note.md_out = "Updated.\n"
	real_replace = os.replace
	replacements = []

	def observe_replace(source, destination):
		replacements.append((source, destination))
		return real_replace(source, destination)

	monkeypatch.setattr("pnbp.models.note.os.replace", observe_replace)

	saved = note.save(notebook)

	assert replacements
	assert replacements[0][1] == path
	assert saved is notebook.notes["alpha"]
	assert path.read_text(encoding="utf-8") == "Updated.\n"


def test_failed_atomic_replace_preserves_file_and_pending_text(note_root, monkeypatch) -> None:
	path = note_root / "alpha.md"
	path.write_text("Original.\n", encoding="utf-8")
	notebook = Notebook()
	note = notebook.notes["alpha"]
	note.md_out = "Pending.\n"

	def fail_replace(source, destination):
		raise OSError("simulated replacement failure")

	monkeypatch.setattr("pnbp.models.note.os.replace", fail_replace)

	with pytest.raises(OSError, match="simulated replacement failure"):
		note.save(notebook)

	assert path.read_text(encoding="utf-8") == "Original.\n"
	assert note.md_out == "Pending.\n"
	assert list(note_root.glob(".alpha.md.*.tmp")) == []


def test_save_rejects_external_changes(note_root) -> None:
	path = note_root / "alpha.md"
	path.write_text("Original.\n", encoding="utf-8")
	notebook = Notebook()
	note = notebook.notes["alpha"]
	note.md_out = "Pending.\n"
	path.write_text("External change.\n", encoding="utf-8")

	with pytest.raises(RuntimeError, match="changed on disk"):
		note.save(notebook)

	assert path.read_text(encoding="utf-8") == "External change.\n"
	assert note.md_out == "Pending.\n"


def test_save_rejects_external_metadata_change(note_root) -> None:
	path = note_root / "alpha.md"
	path.write_text("Original.\n", encoding="utf-8")
	notebook = Notebook()
	note = notebook.notes["alpha"]
	note.md_out = "Pending.\n"
	original_stat = path.stat()
	os.utime(
		path,
		ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns + 1_000_000_000),
	)

	with pytest.raises(RuntimeError, match="changed on disk"):
		note.save(notebook)

	assert path.read_text(encoding="utf-8") == "Original.\n"
	assert note.md_out == "Pending.\n"


def test_save_preserves_loaded_uppercase_extension(note_root) -> None:
	uppercase_path = note_root / "alpha.MD"
	uppercase_path.write_text("Original.\n", encoding="utf-8")
	notebook = Notebook()
	note = notebook.notes["alpha"]
	note.md_out = "Updated.\n"

	note.save(notebook)

	assert uppercase_path.read_text(encoding="utf-8") == "Updated.\n"
	assert not (note_root / "alpha.md").exists()
