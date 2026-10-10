"""Notebook file discovery, loading, and safe note writes."""

import os
import re
import stat
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from pretty_notebook.helpers import _convert_datetime
from pretty_notebook.models.components import Link, Tag, Url, CodeBlock


@dataclass(frozen=True)
class ContentView:
	"""Components derived from one exact current Markdown value."""

	md: str
	links: tuple[Link, ...]
	tags: tuple[Tag, ...]
	urls: tuple[Url, ...]
	codeblocks: tuple[CodeBlock, ...]


def parse_content(text):
	tags = tuple(Tag(f"#{value.lstrip('#')}") for value in dict.fromkeys(Tag.collect_tags(text)))
	if "#pnbp" in tags:
		return ContentView(text, (), (Tag("#pnbp"),), (), ())
	return ContentView(
		text,
		tuple(Link(value.strip()) for value in dict.fromkeys(re.findall(Link.MDS_INT_LNK, text))),
		tags,
		tuple(Url(value) for value in dict.fromkeys(Url.collect_urls(text))),
		tuple(CodeBlock(value) for value in re.findall(CodeBlock.MD_CODE, text) if value.split()),
	)


def retain_edit_draft(root, text):
	"""Retain editor text privately when an explicit save cannot complete."""
	state = Path(root) / ".pnbp"
	drafts = state / "drafts"
	if state.is_symlink() or drafts.is_symlink():
		raise OSError("Refusing to write a draft through a symlinked state directory.")
	drafts.mkdir(parents=True, exist_ok=True, mode=0o700)
	fd, filename = tempfile.mkstemp(prefix="edit-", suffix=".md", dir=drafts)
	try:
		with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
			stream.write(text)
			stream.flush()
			os.fsync(stream.fileno())
	except BaseException:
		Path(filename).unlink(missing_ok=True)
		raise
	return Path(filename)


def iter_note_files(notebook) -> Iterator[Path]:
	""" an internal method to safely iterate the "flat" notebook.NOTE_PATH/
		directory, a "single", or full "recur"(sive) path,
		including (if advised, not by default) "all" (i.e. incl. hidden)
	"""

	root = Path(notebook.NOTE_PATH).expanduser().resolve()
	mode = notebook.config.get("NOTE_NESTED", "flat")
	include_hidden = mode == "all"

	if mode not in {"flat", "single", "recurs", "all"}:
		raise ValueError(f"Unknown NOTE_NESTED mode: {mode!r}")

	def markdown_files(directory: Path) -> list[Path]:
		return sorted(
			path
			for path in directory.iterdir()
			if path.is_file() and path.suffix.lower() == ".md"
		)

	def child_directories(directory: Path) -> list[Path]:
		return sorted(
			path
			for path in directory.iterdir()
			if (
				path.is_dir()
				and not path.is_symlink()
				and path.name not in notebook.SKIP_DIRECTORIES
				and (include_hidden or not path.name.startswith("."))
			)
		)

	yield from markdown_files(root)

	if mode == "flat":
		return

	first_level = child_directories(root)

	if mode == "single":
		for directory in first_level:
			yield from markdown_files(directory)
		return

	pending = list(reversed(first_level))

	while pending:
		directory = pending.pop()
		yield from markdown_files(directory)
		pending.extend(reversed(child_directories(directory)))


def read_note(notebook, f):
	"""
	:param str f: the .md note to open
	"""
	from pretty_notebook.models.note import Note

	root = Path(notebook.NOTE_PATH).expanduser().resolve()
	raw_path = f"{f.name}.md" if isinstance(f, Note) else f
	path = Path(raw_path).expanduser()

	if not path.is_absolute():
		path = root / path

	path = path.resolve()

	try:
		relative_path = path.relative_to(root)
	except ValueError as e:
		raise ValueError("Note path escapes NOTE_PATH") from e

	if path.suffix.lower() != ".md":
		raise ValueError(f"Not a Markdown note: {path}")

	text = path.read_text(encoding="utf-8")
	file_stat = path.stat()
	note_name = relative_path.with_suffix("").as_posix()

	n = Note(
		name=note_name,
		md=text,
		links=[m.strip() for m in re.findall(Link.MDS_INT_LNK, text)],
		tags=Tag.collect_tags(text),
		urls=Url.collect_urls(text),
		codeblocks=re.findall(CodeBlock.MD_CODE, text),
		mtime=_convert_datetime(file_stat.st_mtime, as_mtime=True),
		)
	n.source_path = relative_path.as_posix()
	n._source_exists = True
	n._source_signature = Note._stat_signature(file_stat)

	return n


def generate_note(notebook, name, md_out, overwrite=False, pnbp=False):
	"""
	:param name: the name of the note (without ".md") to generate
	:param md_out: the desired string to save to the notebook at "name.md"
	:param overwrite: if overwrite=True, allow existing file to be re-written
	:param pnbp: if pnbp=True, tagging #pnbp to track and ignore
	"""
	from pretty_notebook.models.note import Note

	if not isinstance(md_out, str):
		raise TypeError(f"md_out must be a str, not {type(md_out)}")

	name = str(name).strip()
	if name.lower().endswith(".md"):
		name = name[:-3]
	if not name:
		raise ValueError("A note name is required.")

	root = Path(notebook.NOTE_PATH).expanduser().resolve()
	destination = (root / f"{name}.md").resolve()

	try:
		relative_path = destination.relative_to(root)
	except ValueError as e:
		raise ValueError("Note path escapes NOTE_PATH") from e

	existing_paths = []
	if destination.parent.exists():
		existing_paths = [
			path
			for path in destination.parent.iterdir()
			if path.name.casefold() == destination.name.casefold()
		]

	if existing_paths and not overwrite:
		raise FileExistsError(f"Cannot generate a new note at {relative_path}.")

	if len(existing_paths) > 1:
		raise FileExistsError(
			f"Cannot choose between case-variant note paths for {relative_path}."
		)

	if existing_paths:
		existing_path = existing_paths[0]
		if existing_path.is_symlink():
			raise ValueError(f"Refusing to overwrite a note symlink: {existing_path}")
		existing_path = existing_path.resolve()
		try:
			existing_relative = existing_path.relative_to(root)
		except ValueError as e:
			raise ValueError("Note path escapes NOTE_PATH") from e
		n = notebook.open_note(existing_relative.as_posix())
	else:
		note_name = relative_path.with_suffix("").as_posix()
		n = Note(
			name=note_name,
			md='',
			links=[],
			tags=[],
			urls=[],
			codeblocks=[],
			mtime='',
		)
		n.source_path = relative_path.as_posix()

	n.md_out = md_out

	if pnbp is True:
		n.md_out += '\n\n--- \n\n#pnbp'

	return n.save(notebook)


def exclusive_create(path, text):
	flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
	fd = os.open(path, flags, 0o666)

	try:
		with os.fdopen(fd, "w", encoding="utf-8") as output:
			fd = None
			output.write(text)
			output.flush()
			os.fsync(output.fileno())
	except Exception:
		if fd is not None:
			os.close(fd)
		path.unlink(missing_ok=True)
		raise


def atomic_replace(note, path, text, source_stat):
	fd, temporary_name = tempfile.mkstemp(
		dir=path.parent,
		prefix=f".{path.name}.",
		suffix=".tmp",
	)
	temporary_path = Path(temporary_name)

	try:
		with os.fdopen(fd, "w", encoding="utf-8") as output:
			fd = None
			output.write(text)
			output.flush()
			os.fsync(output.fileno())

		os.chmod(temporary_path, stat.S_IMODE(source_stat.st_mode))

		current_stat = path.stat()
		current_text = path.read_text(encoding="utf-8")
		if (
			note._stat_signature(current_stat) != note._stat_signature(source_stat)
			or current_text != note.md
		):
			raise RuntimeError(f"Cannot save {note.name}: source changed on disk.")

		os.replace(temporary_path, path)
	finally:
		if fd is not None:
			os.close(fd)
		temporary_path.unlink(missing_ok=True)
