# Browser assets

`apps/web/static/asset-manifest.json` records reviewed versions, versioned local
paths, SHA-256 checksums, SHA-384 browser integrity values, pinned CDN URLs,
dependencies, and license notices. Highlight.js 10.7.2 and Mermaid 12.0.0 retain
their reviewed versions. Bootstrap layout CSS/JavaScript, Popper, and Bootstrap
Icons CSS/fonts have been removed.

Set `PNBP_ASSET_MODE` before starting the web process:

- `auto` (default) uses verified local files, falling back to the manifest's
  exact CDN URLs when files are missing. Startup logs the missing assets.
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
reviewed change. Mermaid loads only for diagram publications; see
[diagram rendering](diagrams.md).

Highlight.js and its theme stylesheet load conditionally for eligible fenced
code. The local copy/label script and optional highlighting policy are
documented in [code presentation](code-tools.md).

## Layout and owner markup

The local `static/css/site.css` supplies light/dark typography, layout, forms,
tables, code, buttons, and responsive navigation. It is loaded in every asset
mode; CDN mode selects only the remaining reviewed third-party libraries.
Navigation uses native `details`/`summary` dropdowns and a POST theme form, so
links and controls work without JavaScript. The footer follows content with a
flex layout instead of reserving a fixed-height spacer. A skip link and visible
focus outlines support keyboard use; reduced-motion preferences disable motion.

`NAV_BRAND`, `NAV_PAGES`, `FOOTER`, and `TITLE` retain their existing owner
controls. Brand/footer HTML keeps the trusted-editor contract. Plain generated
HTML and `.img-fluid` images remain supported. Small compatibility rules cover
`.container`, `.btn`, `.btn-link`, `.form-control`, `.form-group`, `.text-muted`,
and `.text-center`; semantic tables work without a framework class. For custom
owner markup, use `.shell`, `.stack`, `.button`, `.button-secondary`, `.field`,
`.notice`, and `.notice-error`. Arbitrary Bootstrap grid, collapse, dropdown,
and component APIs are no longer shipped. Convert those custom snippets to
semantic HTML or supply owner styles; published Markdown needs no migration.

## Inline icons

The project-owned set has five symbols: `sun`, `moon`, `book`, `globe`, and
`external`. Templates use `{{ icon('moon') | safe }}`; the same renderer supplies
external-link symbols in generated HTML. Sizes are `sm`, `md`, and `lg`; styles
are `default` and `muted`. A decorative symbol is hidden from assistive
technology. Pass `label='Notebook'` for a standalone symbol; labels are escaped
and become the SVG's accessible name. Theme actions retain visible text.

The server displays the five old empty `bi` icon elements as equivalent SVGs
without changing saved settings or publication revisions. Literal code and
unknown markup remain intact. Replace custom icon-only branding with text or
an explicitly named SVG when editing owner settings. Unknown Bootstrap Icons
are no longer available. Both versioned and older duplicate icon fonts/CSS are
removed, so neither local nor CDN mode requests an icon font.
