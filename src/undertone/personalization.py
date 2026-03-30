"""Personalized dictation helpers: styles, dictionary, and snippets."""

from __future__ import annotations

import re
from collections.abc import Mapping

DEFAULT_APP_STYLES: dict[str, str] = {
    "terminal": "literal",
    "code_editor": "minimal",
    "chat": "casual",
    "email": "polished",
    "docs": "polished",
    "browser": "balanced",
    "generic": "balanced",
}

STYLE_ALIASES = {
    "auto": "auto",
    "literal": "literal",
    "raw": "literal",
    "minimal": "minimal",
    "min": "minimal",
    "casual": "casual",
    "chat": "casual",
    "balanced": "balanced",
    "default": "balanced",
    "normal": "balanced",
    "polished": "polished",
    "formal": "polished",
}


def normalize_style(style: str, allow_auto: bool = True) -> str:
    """Normalize a style label to a supported internal value."""
    normalized = style.strip().lower().replace("-", "_").replace(" ", "_")
    resolved = STYLE_ALIASES.get(normalized, "balanced")
    if resolved == "auto" and not allow_auto:
        return "balanced"
    return resolved


def resolve_style(
    style_setting: str,
    app_styles: Mapping[str, str] | None,
    app_category: str,
) -> str:
    """Resolve the effective cleanup style for the current app category."""
    style = normalize_style(style_setting, allow_auto=True)
    if style != "auto":
        return style

    merged_styles = dict(DEFAULT_APP_STYLES)
    if app_styles:
        merged_styles.update({str(key): str(value) for key, value in app_styles.items()})

    category = app_category if app_category in merged_styles else "generic"
    return normalize_style(merged_styles.get(category, "balanced"), allow_auto=False)


def normalize_spoken_text(text: str) -> str:
    """Normalize a spoken phrase for resilient exact-match checks."""
    normalized = text.lower().replace("’", "'")
    parts = re.findall(r"[a-z0-9']+", normalized)
    return " ".join(parts)


def expand_snippet(text: str, snippets: Mapping[str, str] | None) -> str | None:
    """Expand a snippet when the spoken text matches a configured trigger."""
    if not text or not snippets:
        return None

    normalized_text = normalize_spoken_text(text)
    for trigger, expansion in sorted(
        snippets.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if normalize_spoken_text(str(trigger)) == normalized_text:
            return str(expansion)

    return None


def apply_dictionary_replacements(
    text: str,
    replacements: Mapping[str, str] | None,
) -> str:
    """Apply user-defined dictionary replacements, longest keys first."""
    if not text or not replacements:
        return text

    result = text
    ordered = sorted(replacements.items(), key=lambda item: len(str(item[0])), reverse=True)
    for spoken, written in ordered:
        pattern = rf"(?<!\w){re.escape(str(spoken))}(?!\w)"
        result = re.sub(pattern, str(written), result, flags=re.IGNORECASE)

    return result
