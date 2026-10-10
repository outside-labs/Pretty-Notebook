# Models and methods

Import the notebook and settings from the package, note types from its models,
and components from their dedicated module:

```python
from pretty_notebook import Notebook, NotebookSettings, SearchHit
from pretty_notebook import Note
from pnbp.models.components import Link, Tag, CodeBlock, Url
```

The [generated API reference](reference.md) provides selected current signatures;
the [workflow tutorial](tutorials.md) runs complete local examples. These imports
refer to the development checkout; follow [versions and support](versions.md)
when using the published wheel.

## Lookup and source content

`nb.notes` maps source names without their terminal `.md` extension to loaded
notes. `nb.get(name, fuzzy=False)` uses exact/normalized lookup and returns `None`
for a miss. `nb.get(name)` additionally permits the legacy close-name fallback.
Commands require explicit `--fuzzy` before using an approximate match.

A note's tuple fields (`name`, `md`, `links`, `tags`, `urls`, `codeblocks`, `mtime`)
are loaded snapshots. Pending edits use `md_out` and `current_md`; current parsed
views use `current_links`, `current_tags`, `current_urls`, and `current_codeblocks`.
Saving returns a refreshed note, and rendering preserves pending edits. The
[editing guide](editing.md) is authoritative for save/discard/concurrency behavior.

## Components

`Link`, `Tag`, `CodeBlock` and `Url` are string subtypes. Positional and named
construction create the same component type. Equality and hashing are exact;
use `matches()` for explicit query normalization. Tags accept a query with or
without `#`; links match note names without optional brackets, section or label.

For path, alias, heading and stable-ID resolution, use `nb.resolve_link()` or
`Link.resolve(nb, source=...)` as described in [links and graph lookup](links.md).
These resolver operations do not use fuzzy guesses.

## Notebook reports and writes

Ordinary discovery, search, graphs and navigation write no source files or
identity state. Each [navigation snapshot](navigation.md) must be rebuilt after
edits, and [traversal](navigation.md#explicit-traversal-history) records visits
only through an explicit history object.

Use `generate_note()` for new source, `Note.save()` for pending source, and the
[checked rename/move operations](links.md#rename-and-move) to preserve IDs and
repair backlinks. Initialize [identities](identities.md) before managed moves.
Saving generated reports as Markdown is an explicit operation; projections
remain rebuildable from source.
