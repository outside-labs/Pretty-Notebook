# Links and graph lookup

The 0.10 development API exposes a read-only graph and shared resolver:

```python
from pnbp import Notebook

nb = Notebook.open("/path/to/notes")
graph = nb.graph_index()
result = graph.resolve("./Introduction#Overview", source="guides/Index.md")
if result.state == "resolved":
    print(result.path, result.note_id, result.heading_state)
print(graph.diagnostics())
print(graph.backlinks("guides/Introduction.md"))
```

Graphs are snapshots rebuilt from Markdown and optional identity metadata. They
include all nested and hidden notes outside reserved state directories, skip
symlink files, and overlay pending text from notes loaded by this notebook.
They create no files. Rebuild after edits; the graph is not stored authority.
Invalid identity metadata must be repaired before graph operations.

Resolution follows these rules:

- `./Note` and `../Note` are relative to the referring note's directory. A source
  path is required, and references cannot escape the notebook.
- `/folder/Note` and `folder/Note` select a notebook-root path. `.md` is optional.
- A bare `Note` first selects a root note. If there is no root match, lookup
  combines basenames, metadata titles, and metadata aliases. Multiple matches
  are ambiguous; no fuzzy guess chooses one.
- `id:UUID` selects an existing stable note identity. IDs never grant access.
- `[[#Heading]]` refers to the source note. Labels after `|` do not affect lookup.
- Matching ignores case, but case-colliding paths are ambiguous even when one
  spelling matches exactly. Explicit paths do not fall back to unrelated aliases.

`nb.resolve_link(target, source=...)` returns a `LinkResolution` with `state`
(`resolved`, `missing`, `ambiguous`, or `invalid`), `path`, `note_id`, candidates,
and an optional heading diagnostic. `Link.resolve(nb, source=...)` uses this
same resolver and returns a note or `None`, without fuzzy matching. Existing
flat publication URLs remain in place until route migration is implemented.

Heading diagnostics recognize Markdown heading IDs, explicit attribute IDs,
and standard generated anchors. A missing heading is reported separately from
a missing note. Custom wiki headings or raw HTML headings can yield `unknown`
when the source diagnostic cannot prove the requested anchor.

The source scanner keeps exact target spans, labels, fragments, whitespace, and
line numbers. Fenced code (including unclosed fences), inline code, raw HTML
code, comments, embedded image references, and escaped wiki syntax are opaque.
Indented lines are conservatively opaque, including indented list content.
This boundary is intended for safe source editing; it is not a replacement
Markdown engine. Rename/move operations and durable recovery are the next
LINK-02 slice.
