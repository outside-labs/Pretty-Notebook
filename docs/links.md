# Links and graph lookup

The 0.10 API exposes a read-only graph and shared resolver:

```python
from pretty_notebook import Notebook

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
same resolver and returns a note or `None`, without fuzzy matching. Flat
publication URLs remain the default; [route migration](routes.md) is explicit.

Heading diagnostics recognize Markdown heading IDs, explicit attribute IDs,
and standard generated anchors. A missing heading is reported separately from
a missing note. Custom wiki headings or raw HTML headings can yield `unknown`
when the source diagnostic cannot prove the requested anchor.

The source scanner keeps exact target spans, labels, fragments, whitespace, and
line numbers. Fenced code (including unclosed fences), inline code, raw HTML
code, comments, embedded image references, and escaped wiki syntax are opaque.
Indented lines are conservatively opaque, including indented list content.
This boundary is intended for safe source editing; it is not a replacement
Markdown engine.

## Rename and move

Initialize identities explicitly before moving notes. Renaming takes a filename
in the existing directory; moving takes a path relative to the notebook root.
The `.md` suffix is optional. Both operations preserve the note UUID, title,
route metadata, and existing aliases, and retain the previous basename as an
additional lookup alias. Save or discard pending in-memory edits first.

```bash
pnbp --notebook ~/notes note rename guides/Introduction Overview --dry-run
pnbp --notebook ~/notes note move guides/Introduction reference/Overview --dry-run
pnbp --notebook ~/notes note move guides/Introduction reference/Overview
```

```python
plan = nb.rename_note("guides/Introduction", "Overview", dry_run=True)
result = nb.move_note("guides/Introduction", "reference/Overview")
```

The plan lists changed files, exact wiki target replacements, existing graph
diagnostics, and proposed old/new flat URL aliases. Preview creates no files,
directories, or locks. URL aliases are proposals for the later route migration;
this local command does not change a published server.

Matching incoming wiki references, including metadata alias references, point
to the new path. Stable `id:UUID` references keep their target. Outgoing relative
links inside a moved note are repaired when their directory context changes.
Labels, fragments, literal code, prose, whitespace, exact newline bytes, and
file permissions are retained. Ambiguous or broken references remain visible
in diagnostics rather than being assigned an arbitrary target. Existing files,
case-colliding destinations, symlink paths, and unresolved external identity
moves are refused. Case-only filenames can be renamed safely.

## Interrupted operations

Each applied move returns an `operation_id`. Before changing note files, it
stores complete original/proposed files and checksums under the private
`.pnbp/operations/OPERATION_ID/` directory. The journal records intent before
each write and progress afterward. Identity metadata is changed last. Writes
are checked and individually atomic; concurrent readers can observe an
intermediate multi-file state. Cooperating writes share the identity lock;
external editors must still be checked before each replacement.

```bash
pnbp --notebook ~/notes note operations
pnbp --notebook ~/notes note recover OPERATION_ID --action resume --dry-run
pnbp --notebook ~/notes note recover OPERATION_ID --action resume
# Or restore the original touched files:
pnbp --notebook ~/notes note recover OPERATION_ID --action rollback --dry-run
pnbp --notebook ~/notes note recover OPERATION_ID --action rollback
```

`nb.recover_move(operation_id, action="resume" | "rollback", dry_run=False)`
provides the same checked recovery. Completed moves can also be rolled back
while their touched files still match the recorded versions. Empty directories
created during a move may remain after rollback.

Unfinished journals block further identity-changing writes and publication. If a process exits
without releasing `.pnbp/metadata.lock`, confirm no operation is running before
removing that stale lock, then preview recovery. A resume requires untouched
files to match their original version. Rollback leaves never-attempted files
alone, including their external edits. Externally changed attempted files block
both operations before recovery writes anything.

For a conflict, preserve the current edited file elsewhere first. Inspect the
journal's numbered `before/` and `after/` payloads, restore the matching recorded
version for the conflicting path if appropriate, then preview recovery again.
Keep those external edits and reapply them deliberately after recovery. Do not
delete a pending journal or silently reset identities. A damaged journal or
checksum mismatch requires restoring a verified backup before using that
journal for recovery; damaged pending journals keep further writes blocked.

Recovery files can contain private source and are stored with owner-only
permissions. Notebook Git commands exclude operation journals, drafts, locks,
and temporary files. Keep completed journals locally for undo; archiving them
after verification is a deliberate filesystem maintenance operation.
