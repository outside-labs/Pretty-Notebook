import json

import pytest

from pnbp import Notebook
from pnbp.commands.code import _extract_all_code_blocks, _extract_code_blocks


@pytest.fixture
def note_root(monkeypatch, tmp_path):
	note_path = tmp_path / "notes"
	note_path.mkdir()
	monkeypatch.setenv("NOTE_PATH", str(note_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	return note_path


def test_explicit_filename_cannot_escape_code_root(note_root) -> None:
	(note_root / "example.md").write_text(
		"```py\n# ../../outside.py\nprint('unsafe')\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	with pytest.raises(ValueError, match="escapes code output directory"):
		_extract_code_blocks(lang="py", note=notebook.notes["example"], nb=notebook)

	assert not (note_root.parent / "outside.py").exists()


def test_absolute_filename_cannot_escape_code_root(note_root) -> None:
	outside = note_root.parent / "absolute.py"
	(note_root / "example.md").write_text(
		f"```py\n# {outside}\nprint('unsafe')\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	with pytest.raises(ValueError, match="absolute code output path"):
		_extract_code_blocks(lang="py", note=notebook.notes["example"], nb=notebook)

	assert not outside.exists()


def test_escaping_output_symlink_is_rejected(note_root) -> None:
	code_root = note_root / "code"
	outside = note_root.parent / "outside"
	code_root.mkdir()
	outside.mkdir()
	try:
		(code_root / "escape").symlink_to(outside, target_is_directory=True)
	except OSError as error:
		pytest.skip(f"symlinks unavailable: {error}")

	(note_root / "example.md").write_text(
		"```py\n# escape/out.py\nprint('unsafe')\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	with pytest.raises(ValueError, match="escapes code output directory"):
		_extract_code_blocks(lang="py", note=notebook.notes["example"], nb=notebook)

	assert not (outside / "out.py").exists()


def test_all_outputs_are_validated_before_any_write(note_root) -> None:
	(note_root / "example.md").write_text(
		"```py\n# safe.py\nprint('safe')\n```\n\n"
		"```py\n# ../../outside.py\nprint('unsafe')\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	with pytest.raises(ValueError, match="escapes code output directory"):
		_extract_code_blocks(lang="py", note=notebook.notes["example"], nb=notebook)

	assert not (note_root / "code" / "safe.py").exists()
	assert not (note_root.parent / "outside.py").exists()


def test_nested_note_output_is_created_inside_code_root(
	note_root,
	monkeypatch,
) -> None:
	monkeypatch.setenv("NOTE_NESTED", "recurs")
	nested = note_root / "topics"
	nested.mkdir()
	(nested / "example.md").write_text(
		"```py\nprint('nested')\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	_extract_code_blocks(
		lang="py",
		note=notebook.notes["topics/example"],
		nb=notebook,
	)

	assert (note_root / "code" / "topics" / "example.py").read_text(
		encoding="utf-8",
	) == "print('nested')\n"


def test_named_python_body_is_preserved_verbatim(note_root) -> None:
	(note_root / "example.md").write_text(
		"```py\n# package/example.py\n"
		"copy = \"python\"\npython_value = \"py\"\n```\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	_extract_code_blocks(lang="py", note=notebook.notes["example"], nb=notebook)

	assert (note_root / "code" / "package" / "example.py").read_text(
		encoding="utf-8",
	) == 'copy = "python"\npython_value = "py"\n'


def test_language_only_block_does_not_raise_or_write(note_root) -> None:
	(note_root / "example.md").write_text("```py\n```\n", encoding="utf-8")
	notebook = Notebook()

	result = _extract_code_blocks(
		lang="py",
		note=notebook.notes["example"],
		nb=notebook,
	)

	assert result == []
	assert not (note_root / "code" / "example.py").exists()


def test_json_extraction_preserves_json_document_type(note_root) -> None:
	json_body = '{"enabled": true, "items": [1, 2]}\n'
	(note_root / "example.md").write_text(
		f"```json\n{json_body}```\n",
		encoding="utf-8",
	)
	notebook = Notebook()

	_extract_all_code_blocks(note=notebook.notes["example"], nb=notebook)

	output = (note_root / "code" / "example.json").read_text(encoding="utf-8")
	assert output == json_body
	assert json.loads(output) == {"enabled": True, "items": [1, 2]}


def test_existing_output_requires_explicit_overwrite(note_root) -> None:
	(note_root / "example.md").write_text(
		"```py\nprint('new')\n```\n",
		encoding="utf-8",
	)
	code_root = note_root / "code"
	code_root.mkdir()
	output = code_root / "example.py"
	output.write_text("keep\n", encoding="utf-8")
	notebook = Notebook()

	with pytest.raises(FileExistsError, match="overwrite"):
		_extract_code_blocks(lang="py", note=notebook.notes["example"], nb=notebook)

	assert output.read_text(encoding="utf-8") == "keep\n"

	_extract_code_blocks(
		lang="py",
		note=notebook.notes["example"],
		nb=notebook,
		overwrite=True,
	)

	assert output.read_text(encoding="utf-8") == "print('new')\n"
