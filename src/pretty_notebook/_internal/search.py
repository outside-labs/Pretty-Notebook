"""Local notebook search; the legacy regex reporter remains compatible."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import islice
from typing import Literal


SearchField = Literal["content", "title", "tag", "any"]


@dataclass(frozen=True)
class SearchHit:
	"""One hit per note; character offsets refer to the matched field's text."""

	name: str
	start: int
	end: int
	excerpt: str
	field: str = "content"


def _tag_filters(tags):
	if isinstance(tags, str):
		tags = (tags,)
	try:
		values = tuple(islice(iter(tags), 17))
	except TypeError as error:
		raise ValueError("Search tags must be a string or an iterable of tag strings.") from error
	if len(values) > 16 or any(
		not isinstance(tag, str) or not 1 <= len(tag.lstrip("#")) <= 64
		or not re.fullmatch(r"#?[A-Za-z]+", tag)
		for tag in values
	):
		raise ValueError("Search accepts at most 16 ASCII-letter tags of 1-64 characters, with an optional '#'.")
	return frozenset(tag.lstrip("#").casefold() for tag in values)


def note_title(note):
	"""Use an explicit identity title when present, otherwise the source name."""
	return note.identity.title if note.identity is not None and note.identity.title else note.name


def search(
	notebook, query: str, *, field: SearchField = "content", tags: str | Iterable[str] = (),
	regex: bool = False, limit: int = 50, offset: int = 0,
) -> list[SearchHit]:
	"""Search current local notes, returning one quiet hit per matching note.

	Exact tag filters are ANDed before matching. ``any`` checks content, then
	title, then sorted tags; offsets and excerpts refer to the first matching
	field. Results stay in source-name order regardless of the selected field.
	"""
	if not isinstance(query, str) or not 1 <= len(query) <= 512:
		raise ValueError("Search query must contain 1-512 characters.")
	if not isinstance(field, str) or field not in {"content", "title", "tag", "any"}:
		raise ValueError("Search field must be content, title, tag, or any.")
	if type(regex) is not bool:
		raise ValueError("Search regex must be a boolean.")
	if type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or offset < 0:
		raise ValueError("Search requires limit 1-200 and a nonnegative offset.")
	filters = _tag_filters(tags)
	try:
		pattern = re.compile(query if regex else re.escape(query), re.IGNORECASE)
	except re.error as error:
		raise ValueError(f"Invalid search regular expression: {error}") from error
	hits = []
	matched = 0
	for name in sorted(notebook.notes):
		note = notebook.notes[name]
		note_tags = tuple(sorted(map(str, note.current_tags))) if filters or field in {"tag", "any"} else ()
		if not filters <= {tag.lstrip("#").casefold() for tag in note_tags}:
			continue
		fields = (
			(field_name, text) for field_name, text in (
				("content", note.current_md), ("title", note_title(note)), ("tag", " ".join(note_tags)),
			) if field == "any" or field_name == field
		)
		match = None
		for matched_field, text in fields:
			match = pattern.search(text)
			if match is not None:
				break
		if match is None:
			continue
		matched += 1
		if matched <= offset:
			continue
		start = max(0, match.start() - 60)
		hits.append(SearchHit(name, match.start(), match.end(), text[start:start + 160], matched_field))
		if len(hits) == limit:
			break
	return hits


def find(notebook, regex):
	""" a user convenience method to effectively grep notebook
	"""
	print(f'regex: {regex}')

	notes = []
	for fn, n in notebook.notes.items():
		p = re.compile(regex)
		if (m := p.search(n.md)):
			print(f'\t -> {fn}')
			print(m)
			print(f'found: {m}')
			notes.append(n)

	print(f'{[n.name for n in notes]}')

	return notes
