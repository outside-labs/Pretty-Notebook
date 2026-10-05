# Code presentation and copying

Inline code has its own compact style. Fenced code stays in a scrollable,
monospace block; published code blocks receive an optional language label and
a keyboard-operable **Copy code** button. Plain pages, home/contact/error pages,
inline-only code, and Mermaid diagrams do not request Highlight.js. Mermaid
continues to use its separate diagram renderer.

The local `static/js/code-tools.js` captures each block's text before any
highlighting. Copying uses that snapshot, including indentation, tabs, Unicode,
notebook syntax, long lines, and trailing newlines. It never copies highlighted
HTML. Fenced rendering keeps code bodies outside Markdown's whitespace
normalization; fence attributes such as `{.python #sample}` remain supported.
Source notes and pending edits retain their existing save/discard contract.
Historical HTML already containing expanded tabs requires republishing from
Markdown to regain the original text.

Copy results appear beside the block and are announced through a polite status
region. Clipboard denial or a missing clipboard API leaves the source readable
and tells the reader to select/copy it manually. No JavaScript is needed to
read or select the underlying `pre`/`code` content. Language labels are assigned
as text, so unknown names cannot become HTML.

Highlighting is optional. Set `PNBP_CODE_HIGHLIGHT=off` before starting the web
process to keep labels and copy controls without loading the syntax runtime.
The default is `on`; other values are rejected. A code block's `nohighlight`
or `no-highlight` class also opts out. Unlabelled/empty blocks do not trigger
the library. Unknown languages retain plain source rather than guessing.
Missing or blocked runtime/style assets keep code and copy controls usable.

The asset resolver supplies the reviewed local or pinned CDN Highlight.js and
theme stylesheet, with integrity attributes. Load them at most once per page,
only when an eligible block needs highlighting. The shared layout no longer
loads the library/style or calls a global highlighter. Both themes retain the
selected `hljs_light`/`hljs_dark` settings.

Enhancement scans at most 10,000 elements and 100 blocks. Highlighting limits
are 100,000 characters per block and 500,000 per pass; larger blocks remain
plain and copyable. Excess blocks remain readable with manual selection.
Repeated page/content events reuse controls; changed code refreshes the copy
snapshot. Existing legacy pages use the same bounded DOM detection.
