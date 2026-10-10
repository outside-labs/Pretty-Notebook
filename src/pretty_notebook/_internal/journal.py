"""Durable local file-change journals with checked resume and rollback."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4


class JournalError(ValueError):
	"""A move needs explicit recovery or conflict resolution."""


@dataclass(frozen=True)
class FileChange:
	path: str
	before: bytes | None
	after: bytes | None
	mode: int = 0o600


def _path(value):
	if not isinstance(value, str) or "\\" in value or "\x00" in value:
		raise JournalError("Invalid journal path.")
	path = PurePosixPath(value)
	if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
		raise JournalError("Journal paths must stay inside the notebook.")
	if value != ".pnbp/metadata.json" and (path.suffix.lower() != ".md" or any(part in {".pnbp", ".git", ".obsidian", "__pycache__"} for part in path.parts)):
		raise JournalError("Journal changes must be Markdown or the identity index.")
	return value


def _parent(root, relative, *, create=False):
	current = Path(root)
	for part in PurePosixPath(_path(relative)).parts[:-1]:
		if current.is_symlink():
			raise JournalError("Refusing a symlinked operation path.")
		if not current.exists():
			if not create:
				return None
			current.mkdir(mode=0o700)
		entries = list(current.iterdir())
		matches = [entry for entry in entries if entry.name.casefold() == part.casefold()]
		if matches and (len(matches) != 1 or matches[0].name != part):
			raise JournalError("Case-colliding destination directories require explicit repair.")
		current = current / part
		if current.is_symlink() or (current.exists() and not current.is_dir()):
			raise JournalError("Operation directories must be regular directories.")
	if not current.exists() and create:
		current.mkdir(mode=0o700)
	return current if current.exists() else None


def read_exact(root, relative):
	"""Read an exact directory spelling, even on case-insensitive filesystems."""
	parent = _parent(root, relative)
	if parent is None:
		return None
	name = PurePosixPath(relative).name
	if not any(entry.name == name for entry in parent.iterdir()):
		return None
	path = parent / name
	if path.is_symlink() or not path.is_file():
		raise JournalError("Operation files must be regular files.")
	return path.read_bytes()


def _digest(value):
	return hashlib.sha256(value).hexdigest() if value is not None else None


def _sync_directory(path):
	fd = os.open(path, os.O_RDONLY)
	try:
		os.fsync(fd)
	finally:
		os.close(fd)


def _save(directory, data):
	fd, name = tempfile.mkstemp(prefix=".journal-", suffix=".tmp", dir=directory)
	try:
		with os.fdopen(fd, "w", encoding="utf-8") as stream:
			json.dump(data, stream, ensure_ascii=False, indent=2)
			stream.write("\n")
			stream.flush()
			os.fsync(stream.fileno())
		os.replace(name, directory / "journal.json")
		_sync_directory(directory)
	finally:
		Path(name).unlink(missing_ok=True)


def _directory(root, operation_id):
	try:
		if str(UUID(operation_id)) != operation_id:
			raise ValueError
	except (ValueError, TypeError, AttributeError) as error:
		raise JournalError("Operation ID must be a canonical UUID.") from error
	directory = Path(root) / ".pnbp" / "operations" / operation_id
	if any(path.is_symlink() for path in (directory, directory.parent, directory.parent.parent)):
		raise JournalError("Refusing symlinked operation state.")
	return directory


def _load(root, operation_id, *, verify_payload=True):
	directory = _directory(root, operation_id)
	try:
		if (directory / "journal.json").is_symlink():
			raise JournalError("Refusing a symlinked operation journal.")
		data = json.loads((directory / "journal.json").read_text(encoding="utf-8"))
	except (OSError, UnicodeError, json.JSONDecodeError) as error:
		raise JournalError(f"Cannot read operation {operation_id}; preserve its recovery files.") from error
	if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1 or data.get("id") != operation_id or data.get("state") not in {"prepared", "applying", "failed", "committed", "rolled_back"}:
		raise JournalError("Unsupported or invalid operation journal; preserve its recovery files.")
	changes, cursor, active = data.get("changes"), data.get("cursor"), data.get("active")
	if not isinstance(changes, list) or type(cursor) is not int or not 0 <= cursor <= len(changes) or (active is not None and (type(active) is not int or active != cursor or not 0 <= active < len(changes))):
		raise JournalError("Invalid operation progress; preserve its recovery files.")
	paths = set()
	for number, change in enumerate(changes):
		if not isinstance(change, dict) or set(change) != {"path", "mode", "before_hash", "after_hash"} or type(change["mode"]) is not int or not 0 <= change["mode"] <= 0o777:
			raise JournalError("Invalid operation change record.")
		path = _path(change["path"])
		if path in paths:
			raise JournalError("Duplicate operation path.")
		paths.add(path)
		for side in ("before", "after"):
			digest = change[f"{side}_hash"]
			if digest is not None:
				if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
					raise JournalError("Invalid recovery payload checksum.")
				if verify_payload:
					_payload(directory, number, side, digest)
	return directory, data


def _payload(directory, number, side, digest):
	if digest is None:
		return None
	path = directory / side / f"{number:04d}"
	if path.is_symlink() or path.parent.is_symlink():
		raise JournalError("Refusing symlinked recovery originals.")
	try:
		value = path.read_bytes()
	except OSError as error:
		raise JournalError("Missing recovery payload; preserve the journal and current files.") from error
	if _digest(value) != digest:
		raise JournalError("Recovery payload checksum mismatch; preserve the journal and current files.")
	return value


def operations(root, *, limit=200):
	if type(limit) is not int or not 1 <= limit <= 200:
		raise ValueError("Operation list limit must be 1-200.")
	parent = Path(root) / ".pnbp" / "operations"
	if parent.is_symlink() or parent.parent.is_symlink():
		raise JournalError("Refusing symlinked operation state.")
	if not parent.exists():
		return ()
	reports = []
	for directory in sorted(parent.iterdir()):
		if directory.is_dir():
			_, data = _load(root, directory.name, verify_payload=False)
			reports.append({"id": data["id"], "state": data["state"], "from": data.get("from"), "to": data.get("to")})
	return tuple(reports[:limit])


def ensure_clear(root):
	parent = Path(root) / ".pnbp" / "operations"
	if parent.is_symlink() or parent.parent.is_symlink():
		raise JournalError("Refusing symlinked operation state.")
	if parent.exists():
		for directory in parent.iterdir():
			if directory.is_dir():
				_, data = _load(root, directory.name, verify_payload=False)
				if data["state"] not in {"committed", "rolled_back"}:
					raise JournalError(f"Unfinished operation {data['id']}; use pnbp note recover before further writes.")


def prepare(root, changes, *, source, destination):
	operation_id = str(uuid4())
	directory = _directory(root, operation_id)
	directory.mkdir(parents=True, mode=0o700)
	data = {"version": 1, "id": operation_id, "state": "prepared", "cursor": 0, "active": None,
		"from": source, "to": destination, "changes": []}
	try:
		for side in ("before", "after"):
			(directory / side).mkdir(mode=0o700)
		for number, change in enumerate(changes):
			_path(change.path)
			for side in ("before", "after"):
				value = getattr(change, side)
				if value is not None:
					fd = os.open(directory / side / f"{number:04d}", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
					with os.fdopen(fd, "wb") as stream:
						stream.write(value)
						stream.flush()
						os.fsync(stream.fileno())
			data["changes"].append({"path": change.path, "mode": change.mode,
				"before_hash": _digest(change.before), "after_hash": _digest(change.after)})
		for side in ("before", "after"):
			_sync_directory(directory / side)
		_save(directory, data)
		_sync_directory(directory.parent)
	except BaseException:
		if not (directory / "journal.json").exists():
			shutil.rmtree(directory)
		raise
	return operation_id


def _write(root, change, before, after):
	if read_exact(root, change["path"]) != before:
		raise JournalError(f"External edit conflicts with recovery at {change['path']}.")
	parent = _parent(root, change["path"], create=after is not None)
	path = Path(root) / change["path"]
	if after is None:
		path.unlink()
		_sync_directory(parent)
		return
	fd, name = tempfile.mkstemp(prefix=".pnbp-change-", suffix=".tmp", dir=parent)
	try:
		with os.fdopen(fd, "wb") as stream:
			stream.write(after)
			stream.flush()
			os.fsync(stream.fileno())
		os.chmod(name, change["mode"])
		if read_exact(root, change["path"]) != before:
			raise JournalError(f"External edit conflicts with recovery at {change['path']}.")
		if before is None:
			if any(entry.name.casefold() == path.name.casefold() for entry in parent.iterdir()):
				raise JournalError(f"Destination collision at {change['path']}.")
			os.link(name, path)
		else:
			os.replace(name, path)
		_sync_directory(parent)
	finally:
		Path(name).unlink(missing_ok=True)


def _steps(root, directory, data, action):
	steps = []
	for number, change in enumerate(data["changes"]):
		before = _payload(directory, number, "before", change["before_hash"])
		after = _payload(directory, number, "after", change["after_hash"])
		current = read_exact(root, change["path"])
		attempted = number < data["cursor"] or number == data["active"]
		if action == "rollback" and not attempted:
			continue
		if action == "resume" and number < data["cursor"]:
			if current != after:
				raise JournalError(f"External edit conflicts with recovery at {change['path']}.")
			continue
		if current != before and (not attempted or current != after):
			raise JournalError(f"External edit conflicts with recovery at {change['path']}.")
		wanted = after if action == "resume" else before
		steps.append((number, change, current, wanted))
	return steps if action == "resume" else list(reversed(steps))


def recover(root, operation_id, *, action="resume", dry_run=False):
	if action not in {"resume", "rollback"}:
		raise ValueError("Recovery action must be resume or rollback.")
	directory, data = _load(root, operation_id)
	if action == "resume" and data["state"] == "rolled_back":
		raise JournalError("A rolled-back operation cannot be resumed; prepare a new move.")
	if action == "rollback" and data["state"] == "rolled_back":
		return {"id": operation_id, "state": "rolled_back", "dry_run": dry_run, "changes": []}
	try:
		steps = _steps(root, directory, data, action)
	except JournalError as error:
		raise JournalError(f"Operation {operation_id}: {error}") from error
	report = {"id": operation_id, "state": data["state"], "action": action, "dry_run": dry_run,
		"changes": [change["path"] for _, change, current, wanted in steps if current != wanted]}
	if dry_run:
		return report
	try:
		for number, change, current, wanted in steps:
			if action == "resume":
				data.update(state="applying", active=number)
				_save(directory, data)
			if current != wanted:
				_write(root, change, current, wanted)
			if action == "resume":
				data.update(cursor=number + 1, active=None)
			else:
				# Reverse order means the remaining attempted changes form a prefix.
				data.update(cursor=number, active=None)
			_save(directory, data)
		data.update(state="committed" if action == "resume" else "rolled_back", active=None)
		_save(directory, data)
	except Exception as error:
		data["state"] = "failed"
		try:
			_save(directory, data)
		except OSError:
			pass
		raise JournalError(f"Operation {operation_id} interrupted; use pnbp note recover. {error}") from error
	report["state"] = data["state"]
	return report
