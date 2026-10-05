# Stable identities (0.10 development)

`pnbp init PATH` now explicitly creates a version-1 `.pnbp/metadata.json` index
alongside settings. It assigns one notebook UUID and a distinct UUID to each
Markdown note, including nested/hidden notes outside reserved state directories.
Identical contents never share an identity. Source hashes help diagnose external
moves; they are not identity or authorization proofs.

Opening or discovering a notebook never creates, updates, or repairs the index.
Missing metadata leaves original Markdown fully usable. Invalid metadata produces
`nb.identity_error` and an `invalid` identity status while ordinary reads remain
available. Identity-changing operations and saves with invalid identity state
fail clearly rather than silently inventing replacements.

```python
from pnbp import Notebook

nb = Notebook("~/notes")
nb.initialize_identities(dry_run=True)
nb.initialize_identities()
print(nb.notebook_id)
print(nb.get("example", fuzzy=False).note_id)
manifest = nb.export_identities()  # independent versioned object; UUIDs unchanged
```

The JSON index contains `version`, `notebook_id`, and a `notes` array. Each record
has `id`, a notebook-relative POSIX Markdown `path`, the last verified exact-byte
`source_hash`, and optional `title`, `aliases`, and `route` metadata. UUIDs and
paths are unique, and credentials/unknown fields are rejected. Titles, paths,
and routes do not define identity. `note.identity` exposes the loaded record;
the legacy `note.aliases` source-section property remains compatible.

Successful supported saves preserve IDs, update the source hash, and register new
notes only when identity state already exists. Plain notebooks without metadata
remain plain until explicit initialization. Exporting/copying the index preserves
its IDs; full notebook/archive export is a separate feature. Metadata can contain
private note paths or titles, so review it before sharing.

## Clone and fork

Copying a notebook with its metadata creates a clone of the same notebook and
notes. Relative paths make the identity index independent of the local root.
Treat clones as copies of the same logical notebook; independent publication
ownership and conflict-aware synchronization remain later features.

To create an independent notebook identity namespace deliberately:

```bash
pnbp --notebook ~/copied-notes identity fork --dry-run
pnbp --notebook ~/copied-notes identity fork
```

Forking assigns a new notebook UUID and new note UUIDs, keeps Markdown and
title/alias/route metadata, and retains the exact previous index in a private
`metadata-before-fork-*.json` backup. The command reports the backup path. A dry
run writes nothing; its proposed UUIDs are provisional. UUIDs never grant access
or change credentials.

## External moves and recovery

```bash
pnbp --notebook ~/notes identity status --json
pnbp --notebook ~/notes identity reconcile old.md directory/new.md --dry-run
pnbp --notebook ~/notes identity reconcile old.md directory/new.md
```

Status reports missing indexed paths, unindexed files, and content-based rename
suggestions. Identical copied content or multiple missing candidates are marked
ambiguous. No match is applied automatically, even when only one candidate
matches. Reconciliation requires an explicit missing source and an existing,
unindexed destination; it preserves the selected UUID. A changed destination
body is reported by `content_matches: false` and still requires that explicit
choice. Case-only external renames work through the same exact-path mechanism.

Reconciliation updates identity metadata only. Use the [checked move commands](links.md#rename-and-move)
to move source files and repair backlinks together. Rerunning initialization preserves identities,
refreshes hashes, and assigns IDs to genuine new copies; it refuses unresolved
missing paths so an external move cannot quietly become a new note identity.

Writes use an exclusive operation lock and atomic metadata replacement. They
validate the index and recheck its original bytes before replacing it. Failed
replacements preserve the previous index and clean up normal locks/temporary
files. A note-file save and its index update are separate writes: if index
updating fails after Markdown was saved, the Markdown remains on disk, pending
text stays available on the original object, and the index can be repaired and
refreshed with explicit initialization. The CLI retains failed editor text as a
private draft. Review the current source before retrying a save.

Keep corrupt indexes and fork backups while repairing state. Restore a verified
index or repair its schema/UUID/path entries explicitly; deleting it and
initializing again intentionally loses the old identities. An interrupted
process can leave `.pnbp/metadata.lock`: remove that lock only after confirming
no identity operation is running, inspect status, then retry. Notebook Git
commands exclude locks, partial files, credentials, and drafts; the portable
metadata index is eligible for an intentional notebook commit.
