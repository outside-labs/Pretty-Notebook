"""Navigation derived exclusively from the current public-index snapshot."""

import asyncio
import posixpath
from urllib.parse import quote, urlencode, urlsplit

from fastapi import HTTPException
from pnbp._routes import SEGMENT, validate_prefix, validate_route

from .public_index import IndexCapacityError

CONTROL_TAGS = {"public", "private", "pnbp"}


def validate_directory(directory):
    if not isinstance(directory, str) or len(directory) > 499 or (directory and any(not SEGMENT.fullmatch(part) for part in directory.split("/"))):
        raise ValueError("Directory must use notebook-relative lowercase ASCII route segments.")
    return directory


class PublicNavigation:
    """One eligible snapshot; relationships never consult private catalog rows."""

    def __init__(self, documents, *, prefix=""):
        self.prefix = validate_prefix(prefix)
        self.documents = tuple(sorted(documents, key=lambda document: document.route))
        self.by_route = {}
        self.destinations = {}
        for document in self.documents:
            validate_route(document.route, allow_namespace=True)
            if document.route in self.by_route:
                raise ValueError("Duplicate public navigation route.")
            self.by_route[document.route] = document
            for route in (document.route, *document.aliases):
                validate_route(route, allow_namespace=True)
                self.destinations.setdefault(route, set()).add(document.route)
        self.outgoing = {
            document.route: {target for href in document.links if (target := self.resolve_link(document.route, href))}
            for document in self.documents
        }
        self.incoming = {document.route: set() for document in self.documents}
        for source, targets in self.outgoing.items():
            for target in targets:
                self.incoming[target].add(source)
        self.positions = {document.route: position for position, document in enumerate(self.documents)}

    def resolve_link(self, source, href):
        if not isinstance(href, str) or not href or len(href) > 2_000 or "\\" in href or any(ord(character) < 32 for character in href):
            return None
        try:
            parsed = urlsplit(href)
        except ValueError:
            return None
        if parsed.scheme or parsed.netloc or parsed.query or "%" in parsed.path:
            return None
        if not parsed.path:
            return source if source in self.by_route else None
        if any(part in {".", "..", ""} for part in parsed.path.lstrip("/").split("/")):
            return None
        path = parsed.path if parsed.path.startswith("/") else posixpath.dirname(source) + "/" + parsed.path
        candidates = [path]
        if self.prefix and path.startswith(self.prefix + "/"):
            candidates.append(path[len(self.prefix):])
        routes = set()
        for candidate in candidates:
            routes.update(self.destinations.get(candidate, ()))
        return next(iter(routes)) if len(routes) == 1 else None

    def index_url(self, directory="", *, limit=50, offset=0):
        validate_directory(directory)
        params = []
        if directory:
            params.append(("directory", directory))
        if limit != 50:
            params.append(("limit", str(limit)))
        if offset:
            params.append(("offset", str(offset)))
        return self.prefix + "/n" + ("?" + urlencode(params) if params else "")

    def link(self, route):
        document = self.by_route[route]
        return {"route": document.route, "title": document.title, "url": self.prefix + document.route}

    def breadcrumbs(self, directory=""):
        validate_directory(directory)
        result = [{"label": "Notebook", "url": self.index_url()}]
        parts = directory.split("/") if directory else []
        result.extend({"label": part, "url": self.index_url("/".join(parts[:position + 1]))}
                      for position, part in enumerate(parts))
        return result

    def directory(self, directory="", *, limit=50, offset=0):
        validate_directory(directory)
        if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or not 0 <= offset <= 10_000:
            raise ValueError("Index requires limit 1-100 and offset 0-10000.")
        prefix = "/" + directory + "/" if directory else "/"
        directories, notes = set(), []
        for document in self.documents:
            if not document.route.startswith(prefix):
                continue
            relative = document.route[len(prefix):]
            if "/" in relative:
                directories.add((prefix + relative.split("/", 1)[0]).lstrip("/"))
            else:
                notes.append({**self.link(document.route), "kind": "note", "sort": document.route})
        items = notes + [{"kind": "directory", "title": path.rsplit("/", 1)[-1],
                          "url": self.index_url(path), "sort": "/" + path + "/"}
                         for path in directories]
        items.sort(key=lambda item: item["sort"])
        return {
            "directory": directory, "items": items[offset:offset + limit], "total": len(items),
            "breadcrumbs": self.breadcrumbs(directory),
            "previous_url": self.index_url(directory, limit=limit, offset=max(0, offset - limit)) if offset else None,
            "next_url": self.index_url(directory, limit=limit, offset=offset + limit) if offset + limit < len(items) else None,
        }

    def page(self, route, *, related=True):
        document = self.by_route.get(route)
        if document is None:
            return None
        directory = posixpath.dirname(route).lstrip("/")
        position = self.positions[route]
        tags = set(document.tags) - CONTROL_TAGS
        relationships = []
        if related:
            for candidate in self.documents:
                if candidate.route == route:
                    continue
                linked_from = candidate.route in self.outgoing[route]
                links_to = candidate.route in self.incoming[route]
                shared = tuple(sorted(tags & set(candidate.tags)))
                if shared or linked_from or links_to:
                    relationships.append({**self.link(candidate.route), "linked_from": linked_from,
                                          "links_to": links_to, "shared_tags": shared})
            relationships.sort(key=lambda result: (-(result["linked_from"] + result["links_to"]), -len(result["shared_tags"]), result["route"]))
        return {
            "current": self.link(route), "breadcrumbs": self.breadcrumbs(directory),
            "index_url": self.index_url(directory),
            "outline": [{"level": heading.level, "title": heading.title,
                         "url": self.prefix + route + "#" + quote(heading.anchor, safe="") if heading.anchor is not None else None}
                        for heading in document.headings],
            "backlinks": [self.link(source) for source in sorted(self.incoming[route])[:100]],
            "previous": self.link(self.documents[position - 1].route) if position else None,
            "next": self.link(self.documents[position + 1].route) if position + 1 < len(self.documents) else None,
            "related": relationships[:10],
        }


async def snapshot_navigation(request):
    try:
        documents = await request.app.state.public_index.snapshot()
    except IndexCapacityError as error:
        raise HTTPException(503, str(error)) from error
    return await asyncio.to_thread(PublicNavigation, documents, prefix=request.scope.get("root_path", ""))
