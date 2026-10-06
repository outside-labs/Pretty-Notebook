"""Bounded, rebuildable views of the currently visible publication catalog."""

import asyncio
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser

from pnbp.models.components import Tag
from tortoise import connections

from .catalog import _read_blob, blob_path

MAX_DOCUMENTS = 5_000
MAX_INDEX_BYTES = 16 * 1024 * 1024
FIELDS = ("any", "title", "content", "tag")


class IndexCapacityError(RuntimeError):
    """The active notebook exceeds the supported simple-index limits."""


class _VisibleText(HTMLParser):
    HIDDEN = {"script", "style", "template", "head"}
    BLOCKS = {"p", "div", "br", "li", "pre", "blockquote", "tr", "td", "th",
              "h1", "h2", "h3", "h4", "h5", "h6", "hr", "section", "article"}
    TAG_LITERALS = {"code", "pre", "a"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.tag_parts = []
        self.hidden = 0
        self.literal = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.HIDDEN:
            self.hidden += 1
        if tag in self.TAG_LITERALS:
            self.literal += 1
            self.tag_parts.append(" ")
        if not self.hidden and tag in self.BLOCKS:
            self.parts.append(" ")
            self.tag_parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.HIDDEN:
            self.hidden = max(0, self.hidden - 1)
        if tag in self.TAG_LITERALS:
            self.literal = max(0, self.literal - 1)
            self.tag_parts.append(" ")
        if not self.hidden and tag in self.BLOCKS:
            self.parts.append(" ")
            self.tag_parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)
            if not self.literal:
                self.tag_parts.append(text)


@dataclass(frozen=True)
class PublicDocument:
    route: str
    title: str
    text: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...]


def _fingerprint(store, rows):
    signature = []
    for row in rows:
        path = blob_path(store.blobs, row["body_hash"])
        if path.is_symlink():
            raise RuntimeError("Publication blobs must be regular files.")
        stamp = path.stat()
        signature.append((row["id"], row["current_revision"], row["canonical_route"],
                          row["title"], row["aliases"], row["body_hash"],
                          stamp.st_ino, stamp.st_size, stamp.st_mtime_ns))
    return tuple(signature)


def _derive(store, rows):
    documents = []
    size = 0
    for row in rows:
        parser = _VisibleText()
        parser.feed(_read_blob(store.blobs, row["body_hash"]))
        parser.close()
        text = re.sub(r"\s+", " ", "".join(parser.parts)).strip()
        tags = tuple(sorted({tag.casefold() for tag in Tag.collect_tags("".join(parser.tag_parts))}))
        size += len(text.encode("utf-8")) + len(row["title"].encode("utf-8"))
        if size > MAX_INDEX_BYTES:
            raise IndexCapacityError("Public index exceeds the 16 MiB visible-text limit.")
        documents.append(PublicDocument(row["canonical_route"], row["title"], text,
                                        tags, tuple(json.loads(row["aliases"]))))
    return tuple(documents)


class PublicIndex:
    """Visibility is applied before deriving snippets, counts or navigation.

    This query boundary must be extended with grants before supporting private
    readers. Only committed current public revisions participate in 0.10.
    """

    def __init__(self, store):
        self.store = store
        self.signature = None
        self.documents = ()

    async def snapshot(self):
        async with self.store.lock:
            rows = await connections.get("default").execute_query_dict(
                "SELECT n.id, n.canonical_route, n.aliases, n.title, n.current_revision, r.body_hash "
                "FROM pnbp_notes n JOIN pnbp_revisions r "
                "ON n.id=r.note_id AND n.current_revision=r.revision "
                "WHERE n.visibility='public' ORDER BY n.canonical_route LIMIT ?",
                [MAX_DOCUMENTS + 1],
            )
            if len(rows) > MAX_DOCUMENTS:
                raise IndexCapacityError("Public index exceeds the 5,000-publication limit.")
            signature = await asyncio.to_thread(_fingerprint, self.store, rows)
            if signature != self.signature:
                documents = await asyncio.to_thread(_derive, self.store, rows)
                self.documents, self.signature = documents, signature
            return self.documents


def normalize_tags(tags):
    if isinstance(tags, str):
        tags = (tags,)
    if not isinstance(tags, (list, tuple)) or len(tags) > 10:
        raise ValueError("Use at most 10 exact tag filters.")
    result = set()
    for tag in tags:
        if tag == "":
            continue
        if not isinstance(tag, str) or not re.fullmatch(r"#?[A-Za-z]{1,64}", tag):
            raise ValueError("Tag filters contain 1-64 ASCII letters, optionally preceded by #.")
        result.add(tag.lstrip("#").casefold())
    return tuple(sorted(result))


def validate_search(query, field, tags, limit, offset):
    if not isinstance(query, str) or not query.strip() or not 1 <= len(query) <= 512:
        raise ValueError("Search query must contain 1-512 characters and cannot be blank.")
    if field not in FIELDS:
        raise ValueError("Search field must be any, title, content or tag.")
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or not 0 <= offset <= 10_000:
        raise ValueError("Search requires limit 1-100 and offset 0-10000.")
    return normalize_tags(tags)


def _excerpt(text, folded_position):
    position = 0
    folded = 0
    for position, character in enumerate(text):
        folded += len(character.casefold())
        if folded > folded_position:
            break
    start, end = max(0, position - 60), min(len(text), position + 140)
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def search_documents(documents, query, *, field="any", tags=(), limit=20, offset=0):
    tags = validate_search(query, field, tags, limit, offset)
    needle = query.casefold()
    matches = []
    total = 0
    for document in documents:
        if not set(tags).issubset(document.tags):
            continue
        values = {"title": document.title, "content": document.text,
                  "tag": " ".join("#" + tag for tag in document.tags)}
        fields = ("title", "content", "tag") if field == "any" else (field,)
        found = next(((name, values[name].casefold().find(needle)) for name in fields
                      if needle in values[name].casefold()), None)
        if found is None:
            continue
        if offset <= total < offset + limit:
            name, position = found
            matches.append({"route": document.route, "title": document.title,
                            "field": name, "excerpt": _excerpt(values[name], position),
                            "tags": list(document.tags)})
        total += 1
    return {"query": query, "field": field, "tags": list(tags), "total": total,
            "limit": limit, "offset": offset, "hits": matches}
