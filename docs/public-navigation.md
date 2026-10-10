# Published notebook navigation

**0.10 release candidate:** this guide describes the current checkout, rather than
the published 0.9.0 package.

The public site provides a generated notebook index at `/n`, with directory
indexes at `/n?directory=guides`. The home page includes the same public index
while retaining the owner's navigation, title, footer, and theme settings.
Directory indexes list direct publications and child directories containing
public notes. Empty directories have an explicit empty state. Index pages
default to 50 entries, accept `limit` 1–100 and `offset` 0–10000, and retain stable
canonical-route ordering while the publication catalog remains unchanged.

Published pages include breadcrumbs, a directory-index link, a heading outline,
deduplicated backlinks, and previous/next links in canonical-route order. The
optional Related notes panel explains outgoing links, incoming links, and shared
topic tags. Explicit relationships rank first, then shared-tag counts, with
canonical route breaking ties. Publication/exclusion/generated control tags
(`#public`, `#private`, `#pnbp`) do not create related results. Add
`?related=false` to a page URL to omit related results.

Indexes and relationships reuse public search's rebuildable snapshot of current
committed public revisions. Private, deleted, historical, orphaned, and newly
uncataloged legacy files do not enter the generated views. Visibility is applied
before titles, counts, headings, or relationships are derived. This remains the
public-only 0.10 boundary; private readers require permission filtering at that
same boundary before a later implementation returns metadata.

Headings and outgoing links come from visible rendered HTML; script, style,
template, and head contents are excluded. The outline uses existing heading IDs,
quotes fragments safely, and shows headings without a usable unique ID as plain
text. It does not rewrite published HTML. Each document contributes at most 100
headings and 200 distinct outgoing links. Backlinks show at most 100 notes;
related results show at most 10. These views also respect the shared 5,000-page
and 16 MiB index limits. All generated labels are escaped.

Relationships resolve only to eligible canonical routes or their unambiguous
aliases, so renamed notes keep working while an old route remains an alias.
External URLs, query-bearing targets, encoded paths, traversal segments, and
missing targets do not generate relationships. Simple relative links resolve
within the current route's directory. Every generated URL honors the configured
deployment prefix. Directory parameters use lowercase ASCII route segments
separated by `/`, with no leading slash, escapes, or traversal.

Back has a normal link to the known directory index, which works without
JavaScript and on direct entry. When a same-origin, in-prefix referrer and prior
browser history establish an internal visit, the small local enhancement calls
browser Back. Malformed, external, or out-of-prefix referrers and unavailable
history APIs retain the index fallback. Modified clicks retain ordinary browser
behavior. No separate browser history, visits database, or tracking is stored;
the opt-in local Python traversal API is documented in [local navigation](navigation.md).
