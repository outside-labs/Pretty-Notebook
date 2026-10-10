# Pretty Notebook 0.10.0

The 0.10 release moves the distribution to `pretty-notebook` and the canonical
import to `pretty_notebook`, while retaining compatible `pnbp` imports and the
`pnbp` executable. Python 3.11 or newer is required. The final `pnbp==0.10.0`
distribution contains metadata only and installs the matching canonical package.

## Installation and upgrade

```sh
python -m pip install pretty-notebook==0.10.0
```

Remove an old `pnbp` distribution before installing the new package because the
old recorded files overlap the new compatibility imports:

```sh
python -m pip uninstall pnbp
python -m pip install pretty-notebook==0.10.0
```

Back up notebooks and server data before upgrading. Settings migration is
explicit and keeps the legacy source as a private backup. See
[package migration](package-migration.md), [notebook settings](settings.md),
[server state](server-state.md), and [VPS upgrades](vps-deployment.md).

## Included behavior

- Explicit notebook settings/profiles, current-content editing, safe saves,
  stable identities, checked renames/moves and backlink repair.
- Flat and hierarchical publication routes, checked hash/ETag publication
  plans, protected pruning and exact image-byte updates.
- Local/public search, reading navigation, notebook/site identity and favicons.
- Local reviewed browser assets, conditional diagrams, exact fenced-code copy.
- Theme families, reference-style appearance controls, per-visitor preferences,
  native menus at every width, icon labels hidden by default, and inset note surfaces.
- Versioned SQLite state, one coordinated Gunicorn instance with one to four
  workers, generated deployment/upgrade bundles and startup-state isolation.

The FastAPI publisher remains a separately installed repository application.
Supported deployment: Linux x86_64, Python 3.11 or 3.14, one Gunicorn instance,
one local SQLite database/data root, one owning notebook, trusted editors and a
TLS reverse proxy. Follow [web deployment](web.md) before exposing a site.

Shared notebook ownership, private-reader roles, browser-author editing,
distributed storage, a packaged web extra, optional container deployments,
the new Markdown engine and macOS protocol handlers are deferred. Hosted
documentation activation and live VPS deployment remain separate operations.
Versioned GitHub source documentation is the canonical release reference.

## Candidate and final release process

`v0.10.0rc1` publishes only the canonical candidate. Exercise its actual PyPI
wheel with fresh notebooks and a 0.9 upgrade before preparing the final version.
The final `v0.10.0` release publishes `pretty-notebook` first, then the
metadata-only `pnbp` distribution. Both use the existing `release.yaml` workflow
and `pypi` environment with trusted publishing. Adapter or service publication
is outside this release.

Checks include the library suite, installed-wheel/compatibility metadata,
representative settings/identity/route/search workflows, strict documentation,
web integration/branch coverage, local JavaScript controls, Linux deployment
validation and the four-worker smoke test. The readiness record retains exact
candidate and final verification evidence.
