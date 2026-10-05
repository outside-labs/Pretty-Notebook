# Browser assets

`apps/web/static/asset-manifest.json` records reviewed versions, versioned local
paths, SHA-256 checksums, SHA-384 browser integrity values, pinned CDN URLs,
dependencies, and license notices. Bootstrap 5.0.0-beta2, Bootstrap Icons 1.5.0,
Highlight.js 10.7.2, and Mermaid 12.0.0 retain their existing versions. Bootstrap
and icons remain until the separate layout/icon replacement tasks are complete.

Set `PNBP_ASSET_MODE` before starting the web process:

- `auto` (default) uses verified local files, falling back to the manifest's
  exact CDN URLs when files are missing. CSS with missing font dependencies
  falls back as a group. Startup logs the missing assets.
- `local` requires every reviewed runtime file and notice. Missing files,
  corrupt checksums, symlinks, or invalid metadata stop startup with an error.
  Runtime scripts, styles, and fonts need no external network connection.
- `cdn` explicitly selects the pinned CDN URLs with browser integrity checks.
  Local files that are present still undergo integrity validation.

The repository includes the local files and notices. From `apps/web`, run
`python install_assets.py --check` during deployment. If a deployment omits
vendored files, `python install_assets.py --fetch` explicitly downloads missing
files and verifies them before atomic installation. Application startup and
requests never download assets. Python deployment requires no Node tooling.
Corrupt files must be restored from a verified checkout before startup.

Versioned manifest assets receive a one-year immutable cache header; the
manifest and unversioned files do not. A script/style Content-Security-Policy
allows the local origin and, only when selected, the pinned CDN origins.
Inline script/style execution remains allowed for the existing trusted-editor
HTML and theme initialization contract. Connections are limited to the site;
objects and framing are disabled. This is not an untrusted-content sanitizer.

Highlight themes are reviewed manifest entries: this installation includes
`default` and `xt256`. Unreviewed themes are rejected before saving layout
settings. Add a new style with its version, hashes, local file, and notice in a
reviewed change. Mermaid continues to load under the current layout; conditional
diagram loading and its execution contract are tracked separately in STC-01.
