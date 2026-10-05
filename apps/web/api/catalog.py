"""Single-notebook publication revisions and immutable rendered bodies."""

import asyncio
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

from tortoise import connections
from tortoise.transactions import in_transaction

SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
DIGEST_PATTERN = re.compile(r"[a-f0-9]{64}\Z")
LEGACY_PAGE_PREFIX = "{% extends 'shared/layout.html' %}\n\n{% block content %}\n\n"
LEGACY_PAGE_SUFFIX = "\n\n{% endblock %}"
CATALOG_SCHEMA = (
    """CREATE TABLE pnbp_notebooks (
        slot TEXT PRIMARY KEY CHECK (slot = 'default'),
        id TEXT NOT NULL UNIQUE
    )""",
    """CREATE TABLE pnbp_notes (
        id TEXT PRIMARY KEY,
        notebook_id TEXT NOT NULL REFERENCES pnbp_notebooks(id),
        canonical_route TEXT NOT NULL UNIQUE,
        aliases TEXT NOT NULL DEFAULT '[]',
        title TEXT NOT NULL,
        visibility TEXT NOT NULL CHECK (visibility IN ('public', 'deleted')),
        current_revision INTEGER NOT NULL CHECK (current_revision >= 1),
        FOREIGN KEY (id, current_revision) REFERENCES pnbp_revisions(note_id, revision)
            DEFERRABLE INITIALLY DEFERRED
    )""",
    """CREATE TABLE pnbp_revisions (
        note_id TEXT NOT NULL REFERENCES pnbp_notes(id),
        revision INTEGER NOT NULL CHECK (revision >= 1),
        body_hash TEXT NOT NULL,
        source_hash TEXT,
        rendered_hash TEXT NOT NULL,
        renderer_fingerprint TEXT,
        feature_flags TEXT NOT NULL,
        published_at TEXT NOT NULL,
        PRIMARY KEY (note_id, revision)
    )""",
)


def publication_body(content):
    """Unwrap known legacy envelopes without evaluating any template syntax."""
    for newline in ("\n", "\r\n", "\r"):
        prefix = LEGACY_PAGE_PREFIX.replace("\n", newline)
        suffix = LEGACY_PAGE_SUFFIX.replace("\n", newline)
        if content.startswith(prefix) and content.endswith(suffix):
            return content[len(prefix):-len(suffix)]
    return content


class _Features(HTMLParser):
    def __init__(self):
        super().__init__()
        self.flags = set()

    def handle_starttag(self, tag, attrs):
        if tag in {"pre", "code"}:
            self.flags.add("code")
        if tag == "table":
            self.flags.add("table")
        if "mermaid" in (dict(attrs).get("class") or "").split():
            self.flags.add("mermaid")


def feature_flags(body):
    parser = _Features()
    parser.feed(body)
    return sorted(parser.flags)


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def blob_path(directory, digest):
    if not isinstance(digest, str) or not DIGEST_PATTERN.fullmatch(digest):
        raise RuntimeError("Invalid publication blob hash; preserve state and restore a verified backup.")
    if directory.is_symlink() or directory.parent.is_symlink():
        raise RuntimeError("Publication storage must not use symlink directories.")
    return directory / f"{digest}.html"


def _read_blob(directory, digest):
    path = blob_path(directory, digest)
    if path.is_symlink():
        raise RuntimeError("Publication blobs must be regular files.")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError("Publication blob checksum mismatch; restore a verified backup.")
    return data.decode("utf-8")


def _write_blob(directory, body):
    data = body.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    target = blob_path(directory, digest)
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    _sync_directory(directory.parent)
    if target.exists() or target.is_symlink():
        _read_blob(directory, digest)
        return digest
    descriptor, name = tempfile.mkstemp(prefix=".body-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(name, target)
        except FileExistsError:
            _read_blob(directory, digest)
        _sync_directory(directory)
    finally:
        Path(name).unlink(missing_ok=True)
    return digest


class PublicationStore:
    """A process-local coordinator; SQLite and immutable blobs are authority."""

    def __init__(self, pages):
        self.pages = Path(pages)
        self.blobs = self.pages / ".blobs"
        self.lock = asyncio.Lock()
        self.notebook_id = None

    async def start(self):
        async with self.lock:
            async with in_transaction() as transaction:
                await transaction.execute_query("INSERT OR IGNORE INTO pnbp_notebooks (slot, id) VALUES ('default', ?)", [str(uuid4())])
                rows = await transaction.execute_query_dict("SELECT id FROM pnbp_notebooks WHERE slot='default'")
                self.notebook_id = rows[0]["id"]
            await self._import_legacy()

    async def _note(self, name, *, connection=None):
        connection = connection or connections.get("default")
        rows = await connection.execute_query_dict("SELECT * FROM pnbp_notes WHERE canonical_route=?", ["/" + name])
        return rows[0] if rows else None

    def _legacy(self, name):
        if not SLUG_PATTERN.fullmatch(name):
            raise ValueError("Invalid publication name.")
        path = self.pages / f"{name}.html"
        if path.is_symlink():
            raise RuntimeError("Legacy publications must be regular files.")
        if not path.is_file():
            return None
        before = path.stat()
        with path.open(encoding="utf-8", newline="") as stream:
            body = publication_body(stream.read())
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise RuntimeError("Legacy publication changed during import; retry from stopped stable state.")
        return body, datetime.fromtimestamp(before.st_mtime, UTC).isoformat()

    async def _revision(self, transaction, note_id, revision, digest, body, published_at):
        await transaction.execute_query(
            "INSERT INTO pnbp_revisions (note_id, revision, body_hash, source_hash, rendered_hash, renderer_fingerprint, feature_flags, published_at) VALUES (?, ?, ?, NULL, ?, NULL, ?, ?)",
            [note_id, revision, digest, digest, json.dumps(feature_flags(body)), published_at],
        )

    async def _create(self, transaction, name, bodies, *, visibility="public"):
        note_id = str(uuid4())
        await transaction.execute_query(
            "INSERT INTO pnbp_notes (id, notebook_id, canonical_route, title, visibility, current_revision) VALUES (?, ?, ?, ?, ?, ?)",
            [note_id, self.notebook_id, "/" + name, name, visibility, len(bodies)],
        )
        for revision, (digest, body, stamp) in enumerate(bodies, start=1):
            await self._revision(transaction, note_id, revision, digest, body, stamp)
        return note_id

    async def _import_legacy(self):
        rows = await connections.get("default").execute_query_dict("SELECT canonical_route FROM pnbp_notes")
        known = {row["canonical_route"] for row in rows}
        imports = []
        for path in sorted(self.pages.iterdir()):
            if path.is_file() and path.suffix == ".html" and SLUG_PATTERN.fullmatch(path.stem) and "/" + path.stem not in known:
                body, stamp = self._legacy(path.stem)
                digest = await asyncio.to_thread(_write_blob, self.blobs, body)
                imports.append((path.stem, digest, body, stamp))
        if imports:
            for name, _, body, stamp in imports:
                if self._legacy(name) != (body, stamp):
                    raise RuntimeError("Legacy pages changed before catalog import; retry from stopped stable state.")
            async with in_transaction() as transaction:
                for name, digest, body, stamp in imports:
                    await self._create(transaction, name, [(digest, body, stamp)])

    async def publish(self, name, body):
        if not SLUG_PATTERN.fullmatch(name):
            raise ValueError("Invalid publication name.")
        async with self.lock:
            note = await self._note(name)
            original = self._legacy(name) if note is None else None
            bodies = []
            if original:
                old_body, old_stamp = original
                old_hash = await asyncio.to_thread(_write_blob, self.blobs, old_body)
                bodies.append((old_hash, old_body, old_stamp))
            digest = await asyncio.to_thread(_write_blob, self.blobs, body)
            bodies.append((digest, body, datetime.now(UTC).isoformat()))
            await self._commit_publication(name, note, bodies)

    async def _commit_publication(self, name, note, bodies):
        async with in_transaction() as transaction:
            if note is None:
                await self._create(transaction, name, bodies)
            else:
                revision = note["current_revision"] + 1
                digest, body, stamp = bodies[-1]
                await self._revision(transaction, note["id"], revision, digest, body, stamp)
                await transaction.execute_query("UPDATE pnbp_notes SET current_revision=?, visibility='public' WHERE id=?", [revision, note["id"]])

    async def read(self, name):
        note = await self._note(name)
        if note is None:
            legacy = self._legacy(name)
            return legacy[0] if legacy else None
        if note["visibility"] != "public":
            return None
        rows = await connections.get("default").execute_query_dict("SELECT body_hash FROM pnbp_revisions WHERE note_id=? AND revision=?", [note["id"], note["current_revision"]])
        if not rows:
            raise RuntimeError("Publication head has no revision; restore a verified backup.")
        return await asyncio.to_thread(_read_blob, self.blobs, rows[0]["body_hash"])

    async def inventory(self):
        rows = await connections.get("default").execute_query_dict("SELECT n.*, r.source_hash, r.rendered_hash, r.renderer_fingerprint, r.feature_flags, r.published_at FROM pnbp_notes n JOIN pnbp_revisions r ON n.id=r.note_id AND n.current_revision=r.revision ORDER BY n.canonical_route")
        result, known = [], {row["canonical_route"] for row in rows}
        for row in rows:
            if row["visibility"] == "public":
                result.append({"pub_name": row["canonical_route"][1:] + ".html", "mod_date": row["published_at"]})
        for path in sorted(self.pages.iterdir()):
            if path.is_file() and path.suffix == ".html" and SLUG_PATTERN.fullmatch(path.stem) and "/" + path.stem not in known:
                _, stamp = self._legacy(path.stem)
                result.append({"pub_name": path.name, "mod_date": stamp})
        return sorted(result, key=lambda item: item["pub_name"])

    async def delete(self, name):
        async with self.lock:
            note = await self._note(name)
            if note and note["visibility"] == "deleted":
                return False
            if note is None:
                legacy = self._legacy(name)
                if legacy is None:
                    return False
                body, stamp = legacy
                digest = await asyncio.to_thread(_write_blob, self.blobs, body)
                async with in_transaction() as transaction:
                    await self._create(transaction, name, [(digest, body, stamp)], visibility="deleted")
            else:
                await connections.get("default").execute_query("UPDATE pnbp_notes SET visibility='deleted' WHERE id=?", [note["id"]])
            return True

    async def collect_orphans(self, *, dry_run=True, limit=200):
        """Collect only unreferenced blobs, including all historical revisions."""
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError("Orphan collection limit must be 1-200.")
        async with self.lock:
            rows = await connections.get("default").execute_query_dict("SELECT DISTINCT body_hash FROM pnbp_revisions")
            referenced = {row["body_hash"] for row in rows}
            for digest in referenced:
                blob_path(self.blobs, digest)
            blob_path(self.blobs, "0" * 64)
            candidates = sorted(path for path in self.blobs.iterdir() if path.suffix == ".html" and DIGEST_PATTERN.fullmatch(path.stem) and path.stem not in referenced) if self.blobs.exists() else []
            for path in candidates[:limit]:
                await asyncio.to_thread(_read_blob, self.blobs, path.stem)
            if not dry_run:
                for path in candidates[:limit]:
                    path.unlink()
                if candidates:
                    _sync_directory(self.blobs)
            return {"dry_run": dry_run, "orphans": [path.stem for path in candidates[:limit]],
                "count": len(candidates), "truncated": len(candidates) > limit}
