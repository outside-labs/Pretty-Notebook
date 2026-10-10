# Appearance in 0.10 development

Layout and component rules live in `apps/web/static/css/site.css`. Each file in
`static/css/themes` contains color tokens only. The available palettes are
`slate` (the previous blue-gray style), `outside` (black and charcoal in dark
mode, with a charcoal header in both modes), `paper` (warm cream and green),
`forest` (green), and `midnight` (deep blue). Each supports light and dark mode.
Only the selected palette is loaded. Themes never control navigation behavior.

Set `APPEARANCE` in portable notebook settings, then publish it with
`pnbp commit-settings`. The same validated contract is used by the library and
`POST /api/layout`:

```json
{
  "APPEARANCE": {
    "palette": "outside",
    "mode": "system",
    "font": "sans",
    "heading_font": "serif",
    "density": "comfortable",
    "radius": 6,
    "reading_width": 58,
    "site_width": 72,
    "custom_css": false
  }
}
```

| Setting | Accepted values |
| --- | --- |
| `palette` | `slate`, `outside`, `paper`, `forest`, `midnight` |
| `mode` | `light`, `dark`, `system`; null preserves the legacy `darkmode` default |
| `font`, `heading_font` | `sans`, `serif`, `mono`; local system fonts |
| `density` | `comfortable`, `compact` |
| `radius` | Integer 0–20 pixels |
| `reading_width` | Integer 30–90 rem, no greater than `site_width` |
| `site_width` | Integer 48–120 rem; still constrained by the viewport |
| `accent`, `header_bg`, `header_text`, `footer_bg`, `footer_text` | Six-digit hex colors or null |
| `button_labels` | Boolean; show icon text or retain it only as an accessible name |
| `nav_breakpoint` | Integer 480–1440 pixels; default 992 |
| `custom_css` | Boolean; enable the persistent owner stylesheet |

Missing fields get defaults. Unknown keys, arbitrary filenames, CSS expressions
and out-of-range values are rejected. Owner-selected color overrides should be
checked for readable contrast; the built-in palette pairs are tested.

Visitors can choose light, dark or system mode and an independent body font in
the Appearance disclosure. Preferences persist for one year in cookies scoped
to the configured URL prefix. System mode follows operating-system changes;
code highlighting and diagram themes follow the displayed mode. The existing
light/dark toggle and older `darkmode` cookies remain supported.

## Shared design-token contract

Colors use `--color-bg`, `--color-surface`, `--color-text`, `--color-text-muted`,
`--color-primary`, `--color-on-primary`, `--color-border`, `--color-focus`,
`--color-error`, `--color-error-surface`, and `--color-code`. Components can
independently use `--nav-bg`, `--nav-text`, `--footer-bg` and `--footer-text`.
Typography uses `--font-body`, `--font-heading` and `--font-mono`; spacing uses
`--space-1` through `--space-8`; shape and width use `--radius-md`,
`--reading-width` and `--site-width`. Palette, font and density are independent.
Daybook and Fieldnotes can adopt this contract without copying notebook layout.

## Persistent advanced CSS

The site owner can upload UTF-8 CSS (up to 64 KiB) using authenticated
`PUT /api/appearance/stylesheet`, with the CSS as the request body. Then enable
`APPEARANCE.custom_css` through the layout API or notebook settings. The file is
stored as `appearance.css` beside persistent `web-settings.json`, outside the
application checkout. The browser loads it after standard styles and validated
appearance overrides. Replacing application code preserves the stylesheet.
The served URL is `/static/custom/appearance.css`, including any URL prefix.

Custom CSS is an advanced owner-controlled feature, like existing owner HTML;
visitors can only choose the documented mode/font preferences. Back up the CSS
with the rest of the data root. An unset or missing stylesheet returns 404.

## Responsive navigation

Branding and compact controls remain visible. Below `nav_breakpoint`, a Menu
button opens the links and Appearance panel. Its expanded state is announced;
Escape closes an open native dropdown first, then the panel, restoring focus.
Desktop links remain visible. Without JavaScript, links stay visible and wrap
within the viewport. The behavior is shared by every palette. `button_labels`
controls visible icon labels while accessible names remain available.
