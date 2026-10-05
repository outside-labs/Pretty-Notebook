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
from pnbp._routes import validate_route

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


class RouteConflict(ValueError):
    """A route or alias already belongs to a different publication."""


class RevisionConflict(ValueError):
    """A checked write no longer matches the current representation."""


def publication_etag(note):
    if note is None or note["visibility"] != "public":
        return None
    values = [note[key] for key in ("id", "current_revision", "canonical_route", "title", "aliases")]
    digest = hashlib.sha256(json.dumps(values, ensure_ascii=False).encode()).hexdigest()
    return f'"{digest}"'


def check_revision(note, expected_etag, *, legacy_exists=False):
    current = publication_etag(note)
    if expected_etag == "*":
        if current is not None or legacy_exists:
            raise RevisionConflict("Publication already exists; refresh the inventory.")
    elif current is None or current != expected_etag:
        raise RevisionConflict("Publication changed; refresh the inventory before retrying.")


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
        classes = (dict(attrs).get("class") or "").split()
        if "mermaid" in classes or tag == "code" and "language-mermaid" in classes:
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
            return None
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
        rows = await connections.get("default").execute_query_dict("SELECT canonical_route, aliases FROM pnbp_notes")
        known = {route for row in rows for route in (row["canonical_route"], *json.loads(row["aliases"]))}
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

    async def _claim(self, name, aliases=(), previous_name=None):
        route = validate_route("/" + name, allow_namespace=True)
        note = await self._note(name)
        if previous_name is not None:
            validate_route("/" + previous_name, allow_namespace=True)
            previous = await self._note(previous_name)
            if previous is None or previous["visibility"] != "public":
                raise RouteConflict("The previous canonical publication does not exist.")
            if note and note["id"] != previous["id"]:
                raise RouteConflict("The destination route already belongs to another publication.")
            note = previous
        claimed = set(aliases)
        for alias in claimed:
            validate_route(alias, allow_namespace=True)
        if note:
            claimed.update(json.loads(note["aliases"]))
            if note["canonical_route"] != route:
                claimed.add(note["canonical_route"])
        claimed.discard(route)
        rows = await connections.get("default").execute_query_dict("SELECT id, canonical_route, aliases FROM pnbp_notes")
        known = set()
        for row in rows:
            owned = {row["canonical_route"], *json.loads(row["aliases"])}
            known.update(owned)
            if (not note or row["id"] != note["id"]) and owned & {route, *claimed}:
                raise RouteConflict("A canonical route or alias already belongs to another publication.")
        for candidate in {route, *claimed} - known:
            if self._legacy(candidate[1:]) is not None:
                # Ordinary legacy updates may import their existing original.
                if candidate != route or previous_name is not None:
                    raise RouteConflict("A route or alias collides with an uncataloged legacy page.")
        return note, sorted(claimed)

    async def preview_routes(self, claims):
        async with self.lock:
            conflicts, seen, sources = [], {}, set()
            for claim in claims:
                try:
                    note, aliases = await self._claim(claim["name"], claim.get("aliases", ()), claim.get("previous_name"))
                    identity = note["id"] if note else "/" + claim["name"]
                    if identity in sources:
                        raise RouteConflict("The same publication appears more than once in the route plan.")
                    sources.add(identity)
                    for route in ("/" + claim["name"], *aliases):
                        if route in seen:
                            raise RouteConflict("Two planned publications claim the same route or alias.")
                        seen[route] = identity
                except (ValueError, RouteConflict) as error:
                    conflicts.append({"name": claim["name"], "detail": str(error)})
            return {"valid": not conflicts, "conflicts": conflicts, "dry_run": True}

    async def publish(self, name, body, *, title=None, aliases=(), previous_name=None,
                      checked=False, expected_etag=None, source_hash=None, renderer_fingerprint=None):
        async with self.lock:
            note, claimed = await self._claim(name, aliases, previous_name)
            original = self._legacy(name) if note is None else None
            if checked:
                check_revision(note, expected_etag, legacy_exists=original is not None)
            bodies = []
            if original:
                old_body, old_stamp = original
                old_hash = await asyncio.to_thread(_write_blob, self.blobs, old_body)
                bodies.append((old_hash, old_body, old_stamp))
            digest = await asyncio.to_thread(_write_blob, self.blobs, body)
            bodies.append((digest, body, datetime.now(UTC).isoformat()))
            if checked:
                return await self._commit_publication(
                    name, note, bodies, title=title, aliases=claimed,
                    checked=True, expected_etag=expected_etag,
                    source_hash=source_hash, renderer_fingerprint=renderer_fingerprint,
                )
            if title is None and not claimed and previous_name is None:
                await self._commit_publication(name, note, bodies)
            else:
                await self._commit_publication(name, note, bodies, title=title, aliases=claimed)

    async def _commit_publication(self, name, note, bodies, *, title=None, aliases=None,
                                  checked=False, expected_etag=None, source_hash=None, renderer_fingerprint=None):
        async with in_transaction() as transaction:
            if checked:
                current_name = note["canonical_route"][1:] if note else name
                current = await self._note(current_name, connection=transaction)
                check_revision(current, expected_etag, legacy_exists=current is None and self._legacy(name) is not None)
                note = current
            if note is None:
                note_id = await self._create(transaction, name, bodies)
            else:
                note_id = note["id"]
                revision = note["current_revision"] + 1
                digest, body, stamp = bodies[-1]
                await self._revision(transaction, note["id"], revision, digest, body, stamp)
                await transaction.execute_query("UPDATE pnbp_notes SET current_revision=?, visibility='public' WHERE id=?", [revision, note["id"]])
            if title is not None or aliases is not None:
                await transaction.execute_query(
                    "UPDATE pnbp_notes SET canonical_route=?, title=?, aliases=? WHERE id=?",
                    ["/" + name, title if title is not None else note["title"] if note else name, json.dumps(aliases or []), note_id],
                )
            if checked:
                await transaction.execute_query(
                    "UPDATE pnbp_revisions SET source_hash=?, renderer_fingerprint=? WHERE note_id=? AND revision=(SELECT current_revision FROM pnbp_notes WHERE id=?)",
                    [source_hash, renderer_fingerprint, note_id, note_id],
                )
            return await self._note(name, connection=transaction)

    async def resolve(self, name):
        validate_route("/" + name, allow_namespace=True)
        rows = await connections.get("default").execute_query_dict(
            "SELECT * FROM pnbp_notes WHERE canonical_route=? OR EXISTS (SELECT 1 FROM json_each(aliases) WHERE value=?)",
            ["/" + name, "/" + name],
        )
        if len(rows) > 1:
            raise RuntimeError("Ambiguous catalog route; preserve state and repair the catalog.")
        return rows[0] if rows and rows[0]["visibility"] == "public" else None

    async def read(self, name):
        page = await self.read_page(name)
        return page["body"] if page else None

    async def read_page(self, name):
        """Read body and feature metadata from the same immutable revision."""
        note = await self._note(name)
        if note is None:
            legacy = self._legacy(name)
            return {"body": legacy[0], "feature_flags": [], "legacy": True} if legacy else None
        if note["visibility"] != "public":
            return None
        rows = await connections.get("default").execute_query_dict("SELECT body_hash, feature_flags, source_hash, renderer_fingerprint FROM pnbp_revisions WHERE note_id=? AND revision=?", [note["id"], note["current_revision"]])
        if not rows:
            raise RuntimeError("Publication head has no revision; restore a verified backup.")
        row = rows[0]
        return {"body": await asyncio.to_thread(_read_blob, self.blobs, row["body_hash"]),
                "feature_flags": json.loads(row["feature_flags"]),
                "legacy": row["source_hash"] is None or row["renderer_fingerprint"] is None}

    async def inventory(self, *, detailed=False):
        rows = await connections.get("default").execute_query_dict("SELECT n.*, r.source_hash, r.rendered_hash, r.renderer_fingerprint, r.feature_flags, r.published_at FROM pnbp_notes n JOIN pnbp_revisions r ON n.id=r.note_id AND n.current_revision=r.revision ORDER BY n.canonical_route")
        result, known = [], {route for row in rows for route in (row["canonical_route"], *json.loads(row["aliases"]))}
        for row in rows:
            if row["visibility"] == "public":
                entry = {"pub_name": row["canonical_route"][1:] + ".html", "mod_date": row["published_at"]}
                if detailed:
                    entry.update({key: row[key] for key in ("id", "notebook_id", "title", "source_hash", "rendered_hash", "renderer_fingerprint")})
                    entry.update(revision=row["current_revision"], etag=publication_etag(row),
                                 aliases=json.loads(row["aliases"]), feature_flags=json.loads(row["feature_flags"]))
                result.append(entry)
        for path in sorted(self.pages.iterdir()):
            if path.is_file() and path.suffix == ".html" and SLUG_PATTERN.fullmatch(path.stem) and "/" + path.stem not in known:
                _, stamp = self._legacy(path.stem)
                entry = {"pub_name": path.name, "mod_date": stamp}
                if detailed:
                    entry.update(etag=None, revision=None, source_hash=None, renderer_fingerprint=None,
                                 detail="Restart from stable storage to import this legacy page before checked publishing.")
                result.append(entry)
        return sorted(result, key=lambda item: item["pub_name"])

    async def delete(self, name, *, checked=False, expected_etag=None):
        async with self.lock:
            if checked:
                async with in_transaction() as transaction:
                    note = await self._note(name, connection=transaction)
                    check_revision(note, expected_etag)
                    await transaction.execute_query("UPDATE pnbp_notes SET visibility='deleted' WHERE id=?", [note["id"]])
                return True
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
