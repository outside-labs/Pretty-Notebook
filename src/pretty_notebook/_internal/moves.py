"""Checked note moves and exact wiki-target repair over a graph snapshot."""

from __future__ import annotations

import hashlib
import json
import posixpath
import stat
from dataclasses import replace
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

from pretty_notebook._internal import identities as _identities, journal as _journal, links as _links, storage as _storage
from pretty_notebook.models.components import Link


def _files(root):
	adapter = SimpleNamespace(NOTE_PATH=str(root), config={"NOTE_NESTED": "all"}, SKIP_DIRECTORIES=_identities._SKIP_DIRECTORIES)
	files = {}
	for path in _storage.iter_note_files(adapter):
		if path.is_symlink():
			continue
		before = path.stat()
		value = path.read_bytes()
		after = path.stat()
		if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
			raise _journal.JournalError("Source changed during move planning; retry from stable files.")
		files[path.relative_to(root).as_posix()] = value
	return files


def _destination(root, source, destination, rename):
	destination = str(destination).strip()
	if not destination or destination.startswith("/") or "\\" in destination or "\x00" in destination:
		raise ValueError("Destination must be a notebook-relative Markdown path.")
	if rename:
		if "/" in destination:
			raise ValueError("Rename takes a filename; use move for another directory.")
		destination = (PurePosixPath(source).parent / destination).as_posix()
	if not destination.lower().endswith(".md"):
		destination += PurePosixPath(source).suffix
	destination = _identities._relative_path(destination)
	parent = _journal._parent(root, destination)
	if parent:
		for entry in parent.iterdir():
			if entry.name.casefold() == PurePosixPath(destination).name.casefold() and entry.relative_to(root).as_posix() != source:
				raise FileExistsError(f"Destination already exists: {destination}")
	return destination


def _target(path):
	return PurePosixPath(path).with_suffix("").as_posix()


def _relative_target(target_path, source_path):
	value = posixpath.relpath(_target(target_path), posixpath.dirname(source_path) or ".")
	return value if value.startswith("../") else f"./{value}"


def _plan(root, source, destination, rename):
	_journal.ensure_clear(root)
	metadata = _journal.read_exact(root, ".pnbp/metadata.json")
	index = _identities.load_index(root)
	if index is None:
		raise _identities.IdentityError("Run pnbp init before moving notes so their identities can be preserved.")
	files = _files(root)
	if set(index.by_path()) - set(files):
		raise _identities.IdentityError("Reconcile missing indexed paths before moving notes.")
	graph = _links.GraphIndex({path: value.decode("utf-8") for path, value in files.items()}, index)
	selection = graph.resolve(source)
	if selection.state != "resolved":
		raise ValueError(f"Move source is {selection.state}; select an unambiguous root path or note ID.")
	old = selection.path
	new = _destination(root, old, destination, rename)
	if old == new:
		return {"from": old, "to": new, "note_id": selection.note_id, "changed_files": [], "replacements": [], "url_aliases": [], "diagnostics": list(graph.diagnostics())}, (), files, metadata
	known = index.by_path()
	if old not in known:
		raise _identities.IdentityError("Initialize this note's identity explicitly before moving it.")
	post_texts = dict(graph.texts)
	post_texts[new] = post_texts.pop(old)
	moved_identity = replace(known[old], path=new, aliases=tuple(dict.fromkeys((*known[old].aliases, PurePosixPath(old).stem))))
	post_index = replace(index, notes=tuple(moved_identity if note.path == old else note for note in index.notes))
	post_graph = _links.GraphIndex(post_texts, post_index)
	replacements, updated = [], {}
	for path, text in graph.texts.items():
		output_path = new if path == old else path
		edits = []
		for target in _links.wiki_targets(text):
			resolved = graph.resolve(target.target, source=path, fragment=target.fragment)
			if resolved.state != "resolved" or not target.target:
				continue
			wanted = new if resolved.path == old else resolved.path
			after = post_graph.resolve(target.target, source=output_path, fragment=target.fragment)
			if resolved.path != old and after.path == wanted and after.state == "resolved":
				continue
			if target.target.startswith("id:"):
				continue
			if target.target.startswith(("./", "../")):
				value = _relative_target(wanted, output_path)
			else:
				value = _target(wanted)
				if target.target.startswith("/"):
					value = "/" + value
			if target.target.lower().endswith(".md"):
				value += PurePosixPath(wanted).suffix
			if value == target.target:
				continue
			edits.append((target.target_start, target.target_end, value))
			replacements.append({"file": path, "output_file": output_path, "line": target.line, "before": target.target, "after": value})
		for left, right, value in reversed(edits):
			text = text[:left] + value + text[right:]
		updated[output_path] = text.encode("utf-8")
	changed = {path: value for path, value in updated.items() if path == new or value != files[path]}
	if any(path != new and path not in known for path in changed):
		raise _identities.IdentityError("Initialize unindexed backlink notes explicitly before moving notes.")
	for path, value in changed.items():
		previous = moved_identity if path == new else known[path]
		known[path] = replace(previous, source_hash=hashlib.sha256(value).hexdigest())
	del known[old]
	new_index = replace(index, notes=tuple(known.values()))
	_identities.IdentityIndex.from_dict(new_index.to_dict())
	new_metadata = (json.dumps(new_index.to_dict(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
	mode = stat.S_IMODE((root / old).stat().st_mode)
	changes = [_journal.FileChange(old, files[old], None, mode), _journal.FileChange(new, None, changed[new], mode)]
	changes.extend(_journal.FileChange(path, files[path], value, stat.S_IMODE((root / path).stat().st_mode)) for path, value in sorted(changed.items()) if path != new)
	changes.append(_journal.FileChange(".pnbp/metadata.json", metadata, new_metadata))
	old_slug, new_slug = Link(_target(old)).slugname, Link(_target(new)).slugname
	report = {"from": old, "to": new, "note_id": moved_identity.id,
		"changed_files": [change.path for change in changes], "replacements": replacements,
		"url_aliases": [{"from": "/" + old_slug, "to": "/" + new_slug}] if old_slug and new_slug and old_slug != new_slug else [],
		"diagnostics": list(graph.diagnostics())}
	return report, tuple(changes), files, metadata


def move_note(notebook, source, destination, *, rename=False, dry_run=False):
	if notebook.unsaved_notes:
		raise ValueError("Save or discard pending edits before moving notes.")
	root = Path(notebook.NOTE_PATH).expanduser().resolve()
	source = getattr(source, "source_path", source)
	if dry_run:
		report, _, _, _ = _plan(root, source, destination, rename)
		return {**report, "dry_run": True, "operation_id": None}
	with _identities.identity_operation(root):
		report, changes, files, metadata = _plan(root, source, destination, rename)
		if notebook.notebook_id is not None and _identities.load_index(root).notebook_id != notebook.notebook_id:
			raise _identities.IdentityError("Notebook identity changed; reopen before moving notes.")
		if not changes:
			return {**report, "dry_run": False, "operation_id": None}
		if _files(root) != files or _journal.read_exact(root, ".pnbp/metadata.json") != metadata:
			raise _journal.JournalError("Source changed before the move; no note files were changed.")
		_destination(root, report["from"], report["to"], False)
		operation_id = _journal.prepare(root, changes, source=report["from"], destination=report["to"])
		_journal.recover(root, operation_id)
	notebook.reload()
	return {**report, "dry_run": False, "operation_id": operation_id}


def recover_move(notebook, operation_id, *, action="resume", dry_run=False):
	if notebook.unsaved_notes:
		raise ValueError("Save or discard pending edits before recovering a move.")
	root = Path(notebook.NOTE_PATH).expanduser().resolve()
	if dry_run:
		return _journal.recover(root, operation_id, action=action, dry_run=True)
	with _identities.identity_operation(root, recovery=True):
		report = _journal.recover(root, operation_id, action=action)
	notebook.reload()
	return report
