# Diagrams on published pages

Mermaid fences render as escaped `<pre class="mermaid">` source. This preserves
readable text when JavaScript is unavailable. Ordinary fenced code remains
independent of diagram execution and retains syntax highlighting.

The publication catalog stores detected feature flags with each immutable
revision. The page reader uses the body and flags from that same revision.
Known plain pages, home, contact, and missing pages do not include a diagram
loader. Diagram pages load the small local controller, which requests the
reviewed Mermaid asset only after finding a usable diagram source. The asset
resolver retains local-first `auto`, strict `local`, and pinned integrity-checked
`cdn` modes from STC-02.

Legacy pages use a DOM fallback scoped to the publication article. It recognizes
`.mermaid` containers and `code.language-mermaid` fences, visits at most 10,000
elements, and processes at most 32 diagrams. No diagram means no Mermaid library
request. Each source is limited to 50,000 characters, the page's total processed
source to 100,000 characters, and a diagram to 500 edges. Oversized sources remain
readable; malformed diagrams, failed downloads, and rendering errors show source
with a status message and leave navigation working.

Themes are restricted to `default`, `dark`, `forest`, `neutral`, and `base`.
Initialization uses Mermaid's strict security mode, disables automatic startup,
and protects security, bounds, and theme settings against diagram directives.
See the upstream [render API](https://mermaid.js.org/config/usage.html#api-usage)
and [secure configuration](https://mermaid.js.org/config/schema-docs/config.html#secure).
The existing trusted-editor boundary still applies to published HTML.

Repeated initialization reuses the loaded library and original sources. Theme
changes redraw once; unchanged content is skipped. Future navigation can call
`window.pnbpDiagrams.render()` or dispatch `pnbp:content`; theme changes can call
`setTheme(theme)` or dispatch `pnbp:theme` with `{theme}` in the event detail. A
full page refresh retries failed asset loading. No Node installation is needed
to deploy or run the Python app. CI uses Node only for the controller's regression
tests; real browser checks verify both local and CDN diagram rendering.
