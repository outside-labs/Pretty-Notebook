"""Validated, portable appearance settings shared by the client and web app."""

import re

PALETTES = ("slate", "outside", "paper", "forest", "midnight", "dark")
THEME_FAMILIES = {"forest": "dark", "paper": "light", "dark": "dark", "midnight": "dark"}
FONTS = ("sans", "serif", "mono")
DEFAULT_APPEARANCE = {
    "palette": "slate", "mode": None, "font": "sans", "heading_font": "sans",
    "density": "comfortable", "radius": 6, "reading_width": 58,
    "site_width": 72, "accent": None, "header_bg": None, "header_text": None,
    "footer_bg": None, "footer_text": None, "custom_css": False, "button_labels": False, "nav_breakpoint": 992,
}


def validate_appearance(value):
    """Return an independent normalized mapping; reject unknown or unsafe values."""
    if not isinstance(value, dict) or set(value) - DEFAULT_APPEARANCE.keys():
        raise ValueError("APPEARANCE must contain only documented appearance keys.")
    result = {**DEFAULT_APPEARANCE, **value}
    choices = {"palette": PALETTES, "mode": (None, "light", "dark", "system"),
               "font": FONTS, "heading_font": FONTS,
               "density": ("comfortable", "compact")}
    for key, options in choices.items():
        if result[key] not in options:
            raise ValueError(f"Invalid appearance {key}.")
    for key, bounds in {"radius": (0, 20), "reading_width": (30, 90), "site_width": (48, 120), "nav_breakpoint": (480, 1440)}.items():
        if type(result[key]) is not int or not bounds[0] <= result[key] <= bounds[1]:
            raise ValueError(f"Appearance {key} must be an integer from {bounds[0]} to {bounds[1]}.")
    if result["reading_width"] > result["site_width"]:
        raise ValueError("Reading width cannot exceed site width.")
    for key in ("accent", "header_bg", "header_text", "footer_bg", "footer_text"):
        if result[key] is not None and (not isinstance(result[key], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", result[key])):
            raise ValueError(f"Appearance {key} must be a six-digit hex color.")
    for key in ("custom_css", "button_labels"):
        if type(result[key]) is not bool:
            raise ValueError(f"Appearance {key} must be a boolean.")
    return result


def appearance_tokens(value):
    """Produce only validated CSS declarations, never arbitrary CSS interpolation."""
    value = validate_appearance(value)
    tokens = {"--radius-md": f'{value["radius"]}px',
              "--reading-width": f'{value["reading_width"]}rem',
              "--site-width": f'{value["site_width"]}rem'}
    for key, token in {"accent": "--color-primary", "header_bg": "--nav-bg",
                       "header_text": "--nav-text", "footer_bg": "--footer-bg",
                       "footer_text": "--footer-text"}.items():
        if value[key] is not None:
            tokens[token] = value[key]
    if value["accent"] is not None:
        tokens["--color-on-primary"] = accent_text_color(value["accent"])
    return ";".join(f"{key}:{item}" for key, item in tokens.items())


def accent_text_color(color):
    """Choose black or white text with the greater contrast on a validated accent."""
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
              for channel in channels]
    luminance = sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    return "#000000" if luminance > 0.179 else "#ffffff"
