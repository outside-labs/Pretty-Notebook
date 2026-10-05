# Note commands and pending edits (0.10 development)

The development checkout adds explicit note commands and notebook selection:

```bash
pnbp --notebook ~/notes note add ideas/first --content 'A first idea.'
pnbp --notebook ~/notes note show ideas/first
pnbp --notebook ~/notes note edit ideas/first
pnbp --profile work note edit ideas/first --file updated.md
pnbp --profile work note edit ideas/first --content ''
```

`note add` never overwrites an existing note. It accepts an empty initial body,
`--content`, or `--file` (`-` reads stdin). `note edit` requires an existing exact
name/path, accepts the same sources, and opens the configured editor when neither
source is supplied. An explicit empty string saves an empty note. Cancellation
saves nothing. Nested paths can be read or edited explicitly even when ordinary
discovery is flat. Reserved state directories and paths outside the notebook
are refused.

Editing loads the source before launching the editor. Save still checks the
loaded source and atomically replaces it; an external edit prevents a stale save.
On a save failure, the entered text is retained in a private mode-0600
`.pnbp/drafts/edit-*.md` file and the command reports its path. Recovery drafts
are excluded from discovery and notebook Git commands. Review the current source
and draft before applying a recovered edit.

Global `--notebook PATH` or `--profile NAME` also applies to existing commands
such as `pprint`, collectors, Git operations, and publication. Selection is scoped
to the command invocation and does not change environment variables. The default
CLI registers an explicit supported command list, keeping internal helper
functions out of the command menu. See [settings and profiles](settings.md).

## Source, pending text, and save results

```python
from pnbp import Notebook

nb = Notebook("~/notes")
note = nb.get("example", fuzzy=False)
note.md_out = note.current_md + "\nAn additional paragraph.\n"
html = nb.convert_to_html(note)  # preserves pending text
note = note.save(nb)             # retain the returned, freshly loaded Note
```

The legacy `Note` tuple fields remain a loaded snapshot. `md` is the source text
read from disk; `links`, `tags`, `urls`, `codeblocks`, and `mtime` describe that
snapshot. They do not change when text is staged.

`md_out` accepts a string or `None`. `None` means no staged text; `""` means an
explicit empty body. `current_md` selects staged text when present, including an
empty body. `is_unsaved` compares staged and loaded text. Reads, search, and
rendering do not save or discard changes. `discard_changes()` clears pending text
and returns the same Note. Notebook reloads require explicit discard authorization
when edits are pending.

`save(nb)` checks for external file/content changes and uses exclusive creation
or atomic replacement. A changed file is reloaded into `nb.notes`; save returns
that fresh Note. The original tuple's `md` remains the old snapshot, and its
pending field is cleared after success. Assign the returned Note to continue
editing the current saved version. A failed save preserves pending text on the
original object. A no-op save can return the same object.

In notebooks with [identity metadata](identities.md), saves preserve note IDs and
update the exact-byte source hash. Index failures retain recoverable Markdown and
report the required repair; ordinary reads never create identity state.

Use `current_content` or the `current_links`, `current_tags`, `current_urls`, and
`current_codeblocks` properties for derived views of pending text. These views
are cached for the exact current Markdown and invalidated whenever `md_out`
changes, including discard and rendering's temporary transformations. Component
collections are tuples. Existing snapshot fields and component string behavior
remain compatible. These views use the existing notebook extraction rules;
they do not introduce a new Markdown parser.

## Quiet search and bounded reports

```python
hits = nb.search("literal [text]", limit=20, offset=0)
hits = nb.search(r"pattern.*", regex=True)
```

Search returns typed hits (`name`, `start`, `end`, `excerpt`) in note-name order.
Offsets refer to characters in `current_md`; excerpts contain at most 160
characters. Literal matching is the default, and matching is case insensitive.
Queries contain 1–512 characters, limits are 1–200, and offsets are nonnegative.
Regex is an explicit local option; invalid expressions fail clearly. Existing
`nb.find(regex)` remains the legacy stored-source reporter. Published-site search
and its broader filters are a separate feature.

```bash
pnbp --profile work search 'literal [text]' --json --limit 20
pnbp --profile work status --json
pnbp --profile work commit-stage --json --limit 100
```

JSON reports use specific fields, bounded rows/text, and redact the active API
token. They contain no complete settings or credentials object. Status is local;
publication preview may read remote page/image inventories but writes no local
or remote files. Preview reports identify `mode: "legacy-0.9"`, page/image actions,
counts, and truncation. They use the existing timestamp comparison and preserve
remote pages by default. They do not claim revision or hash concurrency checks;
those arrive with PUB-05. Existing one-notebook ownership and explicit-prune
restrictions still apply.

Settings, storage, rendering, search, and publishing now live in focused modules,
with Notebook retaining its convenient public methods. Core imports still use
the existing runtime dependencies and do not load the optional web framework.
