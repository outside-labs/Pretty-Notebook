# Versions and support

The stable published package is `pnbp==0.9.0`, supporting the Python library and
CLI on Python 3.11 or newer. Its [release notes](release-0.9.0.md) define the
installed-wheel contract. The [candidate notes](release-0.9.0rc1.md) and
[readiness record](release-0.9.0-readiness.md) retain their historical meaning.

The current repository contains features targeting **0.10 development**:
explicit notebook settings/profiles, current-content editing, identities,
checked moves/routes/publication, field/tag search, navigation and managed
favicons. Package metadata now prepares `pretty-notebook==0.10.0.dev0`, with
`pretty_notebook` as the canonical import and compatible `pnbp` imports/CLI.
See [package migration](package-migration.md); no 0.10 release is announced.
Use an editable checkout for these APIs; the 0.9.0 wheel cannot be assumed to
provide them merely because a development page describes them.

The repository Markdown is the canonical documentation. The documentation
build reads that source and the current package for API signatures and CLI help.
There is one source page per topic; the [tutorial](tutorials.md) links those
contracts together. To inspect a release's historical source, select its tag in
GitHub rather than treating `main` as the installed release's reference.

The FastAPI publisher is a separate repository application with its own pinned
dependencies. Its supported deployment is one Gunicorn instance with up to four workers,
one local SQLite database and one default notebook behind a TLS proxy. Follow [web deployment](web.md)
for the current contract. Shared notebook ownership, reader roles and distributed
or multi-host storage are deferred. macOS protocol handlers remain unsupported.

Sphinx/MyST build tools are documentation-only and require Python 3.12 or newer;
CI uses Python 3.14. This does not alter the library's Python 3.11 support.
See [building the documentation](building.md) for a clean local build.

The Read the Docs configuration is prepared, but hosted activation, a custom
domain and documentation publication require separate authorization. Repository
links remain the published documentation entry points until that work is complete.
