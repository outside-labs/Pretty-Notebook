"""Versioned local identities, independent of names and authorization."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from uuid import UUID, uuid4

from pretty_notebook._internal import storage as _storage, journal as _journal


class IdentityError(ValueError):
	"""Identity state needs explicit repair; Markdown remains readable."""


_SKIP_DIRECTORIES = {".pnbp", ".git", ".obsidian", "__pycache__"}


def _uuid(value):
	try:
		if not isinstance(value, str):
			raise ValueError
		return str(UUID(value))
	except ValueError as error:
		raise IdentityError("Invalid UUID in metadata.json; restore a verified index or repair it explicitly.") from error


def _relative_path(value):
	if not isinstance(value, str) or "\\" in value:
		raise IdentityError("Identity paths must be relative POSIX Markdown paths.")
	path = PurePosixPath(value)
	if path.is_absolute() or any(part in {"", ".", ".."} | _SKIP_DIRECTORIES for part in value.split("/")) or path.suffix.lower() != ".md":
		raise IdentityError("Identity paths must stay inside the notebook and outside reserved state directories.")
	return path.as_posix()


@dataclass(frozen=True)
class NoteIdentity:
	id: str
	path: str
	source_hash: str | None = None
	title: str | None = None
	aliases: tuple[str, ...] = ()
	route: str | None = None

	def to_dict(self):
		return {"id": self.id, "path": self.path, "source_hash": self.source_hash,
			"title": self.title, "aliases": list(self.aliases), "route": self.route}


@dataclass(frozen=True)
class IdentityIndex:
	notebook_id: str
	notes: tuple[NoteIdentity, ...]

	def by_path(self):
		return {note.path: note for note in self.notes}

	def to_dict(self):
		return {"version": 1, "notebook_id": self.notebook_id,
			"notes": [note.to_dict() for note in sorted(self.notes, key=lambda note: note.path)]}

	@classmethod
	def from_dict(cls, data):
		if not isinstance(data, dict) or set(data) != {"version", "notebook_id", "notes"} or type(data["version"]) is not int or data["version"] != 1:
			raise IdentityError("Unsupported or invalid metadata.json schema; use version 1 or restore a verified index.")
		if not isinstance(data["notes"], list):
			raise IdentityError("metadata.json notes must be an array.")
		notebook_id = _uuid(data["notebook_id"])
		ids, paths, notes = {notebook_id}, set(), []
		for value in data["notes"]:
			if not isinstance(value, dict) or not {"id", "path"} <= set(value) or set(value) - {"id", "path", "source_hash", "title", "aliases", "route"}:
				raise IdentityError("Invalid note identity fields; credentials cannot be stored in metadata.json.")
			note_id, path = _uuid(value["id"]), _relative_path(value["path"])
			if note_id in ids or path in paths:
				raise IdentityError("Duplicate identity or note path in metadata.json; restore or repair the index explicitly.")
			digest = value.get("source_hash")
			aliases = value.get("aliases", [])
			if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
				raise IdentityError("Invalid source hash in metadata.json.")
			if any(value.get(key) is not None and not isinstance(value[key], str) for key in ("title", "route")) or not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
				raise IdentityError("Identity title/route must be strings; aliases must be a string array.")
			ids.add(note_id)
			paths.add(path)
			notes.append(NoteIdentity(note_id, path, digest, value.get("title"), tuple(aliases), value.get("route")))
		return cls(notebook_id, tuple(notes))


def load_index(root):
	path = Path(root) / ".pnbp" / "metadata.json"
	if path.is_symlink():
		raise IdentityError("Refusing a symlinked identity index; restore a regular metadata.json file.")
	if not path.exists():
		return None
	try:
		return IdentityIndex.from_dict(json.loads(path.read_text(encoding="utf-8")))
	except (UnicodeError, json.JSONDecodeError) as error:
		raise IdentityError("Invalid JSON in metadata.json; keep the original and restore or repair the index.") from error
	except OSError as error:
		raise IdentityError("Cannot read metadata.json; preserve it and check its permissions before retrying.") from error


def _snapshot(root):
	root = Path(root).expanduser().resolve()
	if not root.exists():
		return {}
	notebook = SimpleNamespace(NOTE_PATH=str(root), config={"NOTE_NESTED": "all"}, SKIP_DIRECTORIES=_SKIP_DIRECTORIES)
	files = {}
	for path in _storage.iter_note_files(notebook):
		if path.is_symlink():
			continue
		before = path.stat()
		digest = hashlib.sha256(path.read_bytes()).hexdigest()
		after = path.stat()
		if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
			raise IdentityError("A note changed while identity state was inspected; retry from a stable notebook.")
		files[_relative_path(path.relative_to(root).as_posix())] = digest
	return files


def identity_status(root, *, limit=200):
	if type(limit) is not int or not 1 <= limit <= 200:
		raise ValueError("Identity status limit must be 1-200.")
	try:
		index = load_index(root)
	except IdentityError as error:
		return {"state": "invalid", "message": str(error), "notebook_id": None}
	if index is None:
		return {"state": "missing", "message": "Run pnbp init PATH to initialize identities explicitly.", "notebook_id": None}
	files, records = _snapshot(root), index.by_path()
	missing = sorted(set(records) - set(files))
	unindexed = sorted(set(files) - set(records))
	candidates = []
	for old in missing:
		digest = records[old].source_hash
		matches = [path for path in unindexed if digest is not None and files[path] == digest]
		duplicate_content = sum(value == digest for value in files.values()) > 1
		duplicate_missing = sum(records[path].source_hash == digest for path in missing) > 1
		if matches:
			candidates.append({"from": old, "candidates": matches[:limit],
				"ambiguous": len(matches) != 1 or duplicate_content or duplicate_missing,
				"candidate_count": len(matches)})
	return {"state": "initialized", "notebook_id": index.notebook_id,
		"missing": missing[:limit], "unindexed": unindexed[:limit], "rename_candidates": candidates[:limit],
		"missing_count": len(missing), "unindexed_count": len(unindexed),
		"truncated": max(len(missing), len(unindexed), len(candidates)) > limit}


@contextmanager
def identity_operation(root, *, recovery=False):
	state = Path(root) / ".pnbp"
	if state.is_symlink():
		raise IdentityError("Refusing to write identity state through a symlinked directory.")
	state.mkdir(parents=True, exist_ok=True, mode=0o700)
	lock = state / "metadata.lock"
	try:
		fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
	except FileExistsError as error:
		raise IdentityError("Identity operation in progress or interrupted; inspect .pnbp/metadata.lock before retrying.") from error
	try:
		os.close(fd)
		if not recovery:
			try:
				_journal.ensure_clear(root)
			except _journal.JournalError as error:
				raise IdentityError(str(error)) from error
		path = state / "metadata.json"
		yield path.read_bytes() if path.exists() else None
	finally:
		lock.unlink(missing_ok=True)


def _write_index(root, index, expected_bytes):
	path = Path(root) / ".pnbp" / "metadata.json"
	if path.is_symlink():
		raise IdentityError("Refusing to replace a symlinked identity index.")
	data = index.to_dict()
	IdentityIndex.from_dict(data)
	fd, temporary = tempfile.mkstemp(prefix=".metadata-", suffix=".tmp", dir=path.parent)
	try:
		with os.fdopen(fd, "w", encoding="utf-8") as stream:
			json.dump(data, stream, indent=2, ensure_ascii=False)
			stream.write("\n")
			stream.flush()
			os.fsync(stream.fileno())
		if (path.read_bytes() if path.exists() else None) != expected_bytes:
			raise IdentityError("Metadata changed during the operation; retain the current files and reopen before retrying.")
		os.replace(temporary, path)
	finally:
		Path(temporary).unlink(missing_ok=True)


def initialize_identities(root, *, dry_run=False):
	root = Path(root).expanduser().resolve()
	def plan():
		original, files = load_index(root), _snapshot(root)
		index = original
		if index is None:
			index = IdentityIndex(str(uuid4()), ())
		known = index.by_path()
		if set(known) - set(files):
			raise IdentityError("Indexed note paths are missing; inspect identity status and reconcile explicitly before initialization.")
		notes = tuple(replace(known[path], source_hash=digest) if path in known else NoteIdentity(str(uuid4()), path, digest) for path, digest in sorted(files.items()))
		updated = IdentityIndex(index.notebook_id, notes)
		action = "initialize" if original is None else "update" if original != updated else "unchanged"
		return updated, len(set(files) - set(known)), action
	if dry_run:
		index, added, action = plan()
	else:
		with identity_operation(root) as expected_bytes:
			index, added, action = plan()
			if load_index(root) != index:
				_write_index(root, index, expected_bytes)
	return {"action": action,
		"notebook_id": index.notebook_id, "note_count": len(index.notes), "new_notes": added, "dry_run": dry_run}


def check_note_write(root, note, expected_notebook_id):
	index = load_index(root)
	if index is None:
		if expected_notebook_id is not None:
			raise IdentityError("Identity index disappeared; restore it before saving this loaded note.")
		return None
	if expected_notebook_id is not None and index.notebook_id != expected_notebook_id:
		raise IdentityError("Notebook identity changed; reopen the notebook before saving.")
	path = _relative_path(note.source_path or f"{note.name}.md")
	current = index.by_path().get(path)
	if note.note_id is not None and (current is None or current.id != note.note_id):
		raise IdentityError("Note identity changed; reopen the notebook before saving.")
	if current is None and set(index.by_path()) - set(_snapshot(root)):
		raise IdentityError("Unresolved external note moves require explicit identity reconciliation before adding identities.")
	return index


def record_saved_note(root, note, index, expected_bytes):
	path = _relative_path(note.source_path)
	known = index.by_path()
	digest = hashlib.sha256((Path(root) / path).read_bytes()).hexdigest()
	identity = replace(known[path], source_hash=digest) if path in known else NoteIdentity(str(uuid4()), path, digest)
	known[path] = identity
	updated = IdentityIndex(index.notebook_id, tuple(known.values()))
	_write_index(root, updated, expected_bytes)
	return updated


def reconcile_identity(root, old_path, new_path, *, dry_run=False):
	old_path, new_path = _relative_path(old_path), _relative_path(new_path)
	def plan():
		index = load_index(root)
		if index is None:
			raise IdentityError("Initialize identities before reconciliation.")
		files, known = _snapshot(root), index.by_path()
		if old_path not in known or old_path in files or new_path not in files or new_path in known:
			raise IdentityError("Reconciliation requires one missing indexed source and one existing unindexed destination.")
		old = known.pop(old_path)
		known[new_path] = replace(old, path=new_path, source_hash=files[new_path])
		return IdentityIndex(index.notebook_id, tuple(known.values())), old.source_hash == files[new_path], old.id
	if dry_run:
		index, matches, note_id = plan()
	else:
		with identity_operation(root) as expected_bytes:
			index, matches, note_id = plan()
			_write_index(root, index, expected_bytes)
	return {"from": old_path, "to": new_path, "note_id": note_id, "content_matches": matches, "dry_run": dry_run}


def fork_identities(root, *, dry_run=False):
	def plan():
		index = load_index(root)
		if index is None:
			raise IdentityError("Initialize identities before forking.")
		new = IdentityIndex(str(uuid4()), tuple(replace(note, id=str(uuid4())) for note in index.notes))
		return index, new
	backup = None
	if dry_run:
		old, new = plan()
	else:
		with identity_operation(root) as expected_bytes:
			old, new = plan()
			fd, name = tempfile.mkstemp(prefix="metadata-before-fork-", suffix=".json", dir=Path(root) / ".pnbp")
			backup = Path(name)
			with os.fdopen(fd, "wb") as stream:
				stream.write((Path(root) / ".pnbp" / "metadata.json").read_bytes())
				stream.flush()
				os.fsync(stream.fileno())
			_write_index(root, new, expected_bytes)
	return {"old_notebook_id": old.notebook_id, "notebook_id": new.notebook_id,
		"note_count": len(new.notes), "backup": str(backup) if backup else None, "dry_run": dry_run}
