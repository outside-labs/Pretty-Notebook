# Search a published notebook

The public search page is `/n/search`; the navigation includes a Search link.
Queries are literal and case-insensitive, including Unicode. Choose titles,
content, tags, or all three fields. Results use canonical publication routes,
sorted by route, and excerpts are rendered as escaped text.

The anonymous read API is `GET /api/search?q=...`. Optional parameters are
`field=any|title|content|tag`, repeated exact `tag=...` filters, `limit=1..100`
(default 20), and `offset=0..10000`. All tag filters must match; they accept an
optional `#` and 1–64 ASCII letters, following the existing tag dialect.
Queries contain 1–512 characters and cannot be blank. Regular expressions are
available only through local notebook search; `regex` is rejected by this API.
JSON excerpts are plain text: clients must escape them when displaying HTML.

```sh
curl --get --data-urlencode 'q=Python' --data 'field=title' \
  --data 'tag=public' https://notebook.example/api/search
```

Search derives visible text and tags from immutable rendered bodies referenced
by the current public catalog. Script, style, template and head content is
excluded; code and link labels do not create tag filters. HTML attributes,
including image paths, are not searchable content. Tags describe published
content and never grant access.

Replacing, renaming or deleting a publication invalidates the derived snapshot.
Historical revisions, orphaned uploads, deleted entries and uncataloged legacy
files cannot become results. Restart imports stable legacy pages through the
existing catalog migration before indexing. The visibility query precedes
snippets, counts and matching; private-reader support must extend that boundary
with permissions before exposing private results.

The simple derived view supports up to 5,000 active publications and 16 MiB of
visible text and titles. Exceeding either limit returns 503 rather than partial
results. The view is rebuildable and does not change authoritative SQLite state
or rendered blobs. The existing one-worker, local-SQLite, trusted-editor profile
continues to apply. URLs include the configured proxy prefix.
