# Publication routes

Flat routes remain the default. Set `ROUTE_MODE` to `hierarchical` and enable
recursive discovery with `NOTE_NESTED: "all"` to publish
`python/Function Definitions.md` at `/python/function-definitions`.
Note UUIDs, source paths, display titles, and public routes remain distinct.

Use `PUBLICATION_ROUTES: {"研究.md": "/research"}` for an explicit route when
a source name cannot produce an ASCII slug. Each route segment accepts lowercase
ASCII letters, digits, and separating hyphens. Traversal, encoded separators,
empty segments, reserved application prefixes, and duplicate canonical routes
fail before local writes or remote publication requests.

`Notebook.publication_routes()` returns a read-only preview of source paths,
identities, titles, canonical routes, candidate flat aliases, and
`legacy_collisions`. Ambiguous aliases are omitted; resolve collisions before
migrating an existing flat publication. Never infer that a flat page belongs to
a new nested source solely from its slug.

`URL_PREFIX: "/notes"` makes generated wiki links and images start at `/notes/`.
Configure the server/proxy with the same ASGI root path. The prefix has no
trailing slash; API_BASE includes the proxy prefix for remote requests.
Heading fragments use the Markdown renderer's heading-ID policy. Local HTML
exports use contained subdirectories matching their canonical routes.

`ROUTE_MODE: "namespaced"` with `NOTEBOOK_SLUG: "field-notes"` prepares
`/n/field-notes/...` routes. This is a mapping for the existing default notebook;
independent notebook ownership and shared pruning remain deferred.
