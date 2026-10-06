# Local notebook search

`Notebook.search()` returns quiet, immutable `SearchHit` values from the notes
currently loaded in memory, including pending edits. It writes no files, makes
no network requests, and does not record visits. Local search includes private
notes; publication eligibility is handled separately by published-site search.

```python
from pnbp import Notebook, SearchHit

nb = Notebook.open("/path/to/notes")
hits = nb.search("literal [café]", limit=20)
titles = nb.search("Guide", field="title")
tag_hits = nb.search("work", field="tag")
filtered = nb.search("recipe", field="any", tags=("food", "#work"))
patterns = nb.search(r"recipe\s+\d+", regex=True)
```

The default `field="content"` preserves the original current-Markdown search.
`title` uses the optional identity metadata title, falling back to the note's
source name. `tag` searches the space-separated, sorted current tags. `any`
checks content first, then title, then tags and returns one hit per note.
Exact tag filters are case insensitive, accept a leading `#`, and require every
specified tag. They use the notebook's existing ASCII-letter tag grammar and
exclude tag-like text inside protected code, links, and URLs.

Every hit has `name`, `start`, `end`, `excerpt`, and `field`. `start` and `end`
are character offsets into the matched field's text, rather than byte offsets.
Excerpts retain plain source text and contain at most 160 characters. An HTML
consumer must escape excerpts before displaying them. Results are ordered by
source name and pagination is stable while the loaded notebook stays unchanged.

Queries contain 1–512 characters. `limit` is an integer from 1–200 and `offset`
is a nonnegative integer counting matching notes. At most 16 exact tag filters
are accepted, each with 1–64 ASCII letters. Invalid options and regular
expressions raise `ValueError`. Regex remains an explicit local option and may
be expensive on large input; it is not a public query language. The existing
`nb.find(regex)` continues to report matches against loaded, saved-source text.

```bash
pnbp --notebook /path/to/notes search 'literal [café]' --json --limit 20
pnbp --profile work search 'Guide' --field title
pnbp --profile work search 'recipe' --field any --tag food --tag work --offset 20
pnbp --profile work search 'recipe\s+\d+' --regex
```

JSON output retains `hits`, `limit`, and `offset`; each hit reports its matched
field. The JSON reporter continues to redact the configured API token.
