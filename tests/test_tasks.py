import pytest

from pnbp import Notebook
from pnbp.commands.tasks import _task_settle
from pnbp.models import Note


@pytest.fixture
def task_notebook(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	return tmp_path


def test_first_task_settlement_creates_completion_log(task_notebook) -> None:
	task_path = task_notebook / "tasks.md"
	task_path.write_text("#tasks\n- [x] wash dishes\n", encoding="utf-8")
	notebook = Notebook()

	_task_settle(nb=notebook)

	assert task_path.read_text(encoding="utf-8") == "#tasks\n- [ ] wash dishes"
	completion = (task_notebook / "_complete.md").read_text(encoding="utf-8")
	assert completion.count("- [x] wash dishes") == 1


def test_recurring_settlement_records_value_before_reset(task_notebook) -> None:
	task_path = task_notebook / "tasks.md"
	task_path.write_text("#tasks\n- [x] water (amount:2)\n", encoding="utf-8")
	notebook = Notebook()

	_task_settle(nb=notebook)

	assert task_path.read_text(encoding="utf-8") == "#tasks\n- [ ] water (amount: )\n"
	completion = (task_notebook / "_complete.md").read_text(encoding="utf-8")
	assert completion.count("- [x] water (amount:2") == 1


def test_new_completion_log_failure_leaves_task_unchanged(
	task_notebook,
	monkeypatch,
) -> None:
	task_path = task_notebook / "tasks.md"
	original = "#tasks\n- [x] water (amount:2)\n"
	task_path.write_text(original, encoding="utf-8")
	notebook = Notebook()
	real_create = Note._exclusive_create

	def fail_completion_create(path, text):
		if path.name == "_complete.md":
			raise OSError("simulated completion-log failure")
		return real_create(path, text)

	monkeypatch.setattr(
		Note,
		"_exclusive_create",
		staticmethod(fail_completion_create),
	)

	with pytest.raises(OSError, match="simulated completion-log failure"):
		_task_settle(nb=notebook)

	assert task_path.read_text(encoding="utf-8") == original
	assert not (task_notebook / "_complete.md").exists()
	assert not notebook.has_unsaved_notes


def test_existing_completion_log_failure_leaves_task_unchanged(
	task_notebook,
	monkeypatch,
) -> None:
	task_path = task_notebook / "tasks.md"
	completion_path = task_notebook / "_complete.md"
	original = "#tasks\n- [x] water (amount:2)\n"
	task_path.write_text(original, encoding="utf-8")
	completion_path.write_text("Earlier completion.\n", encoding="utf-8")
	notebook = Notebook()
	real_replace = Note._atomic_replace

	def fail_completion_replace(self, path, text, source_stat):
		if path.name == "_complete.md":
			raise OSError("simulated completion-log failure")
		return real_replace(self, path, text, source_stat)

	monkeypatch.setattr(Note, "_atomic_replace", fail_completion_replace)

	with pytest.raises(OSError, match="simulated completion-log failure"):
		_task_settle(nb=notebook)

	assert task_path.read_text(encoding="utf-8") == original
	assert completion_path.read_text(encoding="utf-8") == "Earlier completion.\n"
	assert not notebook.has_unsaved_notes


def test_retry_after_task_write_failure_does_not_duplicate_completion(
	task_notebook,
	monkeypatch,
) -> None:
	task_path = task_notebook / "tasks.md"
	original = "#tasks\n- [x] water (amount:2)\n"
	task_path.write_text(original, encoding="utf-8")
	notebook = Notebook()
	real_replace = Note._atomic_replace
	failed = False

	def fail_task_once(self, path, text, source_stat):
		nonlocal failed
		if path.name == "tasks.md" and not failed:
			failed = True
			raise OSError("simulated task-write failure")
		return real_replace(self, path, text, source_stat)

	monkeypatch.setattr(Note, "_atomic_replace", fail_task_once)

	with pytest.raises(OSError, match="simulated task-write failure"):
		_task_settle(nb=notebook)

	completion_path = task_notebook / "_complete.md"
	assert task_path.read_text(encoding="utf-8") == original
	assert completion_path.read_text(encoding="utf-8").count("- [x] water") == 1
	assert not notebook.has_unsaved_notes

	_task_settle(nb=notebook)

	assert task_path.read_text(encoding="utf-8") == "#tasks\n- [ ] water (amount: )\n"
	assert completion_path.read_text(encoding="utf-8").count("- [x] water") == 1


def test_later_identical_completion_is_not_treated_as_retry(task_notebook) -> None:
	task_path = task_notebook / "tasks.md"
	original = "#tasks\n- [x] water (amount:2)\n"
	task_path.write_text(original, encoding="utf-8")
	notebook = Notebook()

	_task_settle(nb=notebook)
	note = notebook.notes["tasks"]
	note.md_out = original
	note.save(notebook)
	_task_settle(nb=notebook)

	completion = (task_notebook / "_complete.md").read_text(encoding="utf-8")
	assert completion.count("- [x] water (amount:2") == 2
	assert completion.count("pnbp:task-settlement") == 2
