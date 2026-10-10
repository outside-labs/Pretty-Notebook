"""Small project-owned SVGs for templates and generated notebook links."""

import re
from html import escape

_SHAPES = {
    "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5Z"/>',
    "book": '<path d="M12 5v15m0-15C9 3 5 3 2 4v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Z"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    "external": '<path d="M14 3h7v7m0-7L11 13M10 5H4a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-6"/>',
}
_SIZES = {"sm": 14, "md": 20, "lg": 24}
_LEGACY = {"eye": "moon", "eye-fill": "sun", "book-fill": "book",
           "globe2": "globe", "box-arrow-up-right": "external"}
_LEGACY_MARKUP = re.compile(
    r"<(?P<literal>pre|code|script|style)\b[^>]*>.*?</(?P=literal)\s*>"
    r"|<i\s+class=(?P<quote>['\"])bi bi-(?P<name>[\w-]+)(?P=quote)"
    r"(?:\s+style=['\"]font-size:10px;['\"])?\s*>\s*</i\s*>",
    re.IGNORECASE | re.DOTALL,
)


def render_icon(name, *, label=None, size="md", variant="default"):
    """Return an inline SVG; adjacent text normally supplies its accessible name."""
    if name not in _SHAPES or size not in _SIZES or variant not in {"default", "muted"}:
        raise ValueError("Choose a supported icon, size (sm/md/lg), and variant (default/muted).")
    accessibility = ('aria-hidden="true"' if label is None else
                     f'role="img" aria-label="{escape(label, quote=True)}"')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="icon icon-{size} icon-{variant}" '
        f'width="{_SIZES[size]}" height="{_SIZES[size]}" viewBox="0 0 24 24" '
        f'{accessibility} focusable="false" fill="none" stroke="currentColor" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">'
        f'{_SHAPES[name]}</svg>'
    )


def replace_legacy_icons(markup):
    """Display the five historical empty icon elements without rewriting storage.

    Leave literal code, script/style blocks, unknown icons, and other HTML intact.
    """
    def replace(match):
        name = _LEGACY.get((match.group("name") or "").lower())
        if name is None:
            return match.group(0)
        label = {"book": "Notebook", "globe": "Published notebook"}.get(name)
        return render_icon(name, label=label, size="sm" if name == "external" else "md")
    return _LEGACY_MARKUP.sub(replace, markup)
