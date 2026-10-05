"""Local notebook search; the legacy regex reporter remains compatible."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchHit:
	name: str
	start: int
	end: int
	excerpt: str


def search(notebook, query, *, regex=False, limit=50, offset=0):
	"""Quiet, bounded current-content search; public-site search comes separately."""
	if not isinstance(query, str) or not 1 <= len(query) <= 512:
		raise ValueError("Search query must contain 1-512 characters.")
	if type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or offset < 0:
		raise ValueError("Search requires limit 1-200 and a nonnegative offset.")
	try:
		pattern = re.compile(query if regex else re.escape(query), re.IGNORECASE)
	except re.error as error:
		raise ValueError("Invalid search regular expression.") from error
	hits = []
	matched = 0
	for name in sorted(notebook.notes):
		text = notebook.notes[name].current_md
		match = pattern.search(text)
		if match is None:
			continue
		matched += 1
		if matched <= offset:
			continue
		start = max(0, match.start() - 60)
		hits.append(SearchHit(name, match.start(), match.end(), text[start:start + 160]))
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
