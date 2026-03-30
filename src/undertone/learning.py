"""Lightweight dictation history and correction learning."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from undertone.config import CONFIG_DIR, ensure_config_dir

LAST_DICTATION_FILE = CONFIG_DIR / "last_dictation.yaml"


@dataclass
class DictationRecord:
    """Most recent dictation event stored for correction learning."""

    raw_text: str
    final_text: str
    cleaned_text: str
    app_category: str
    style: str
    timestamp: str


def save_last_dictation(
    raw_text: str,
    final_text: str,
    cleaned_text: str,
    app_category: str,
    style: str,
) -> None:
    """Persist the most recent dictation for later learning."""
    ensure_config_dir()
    record = DictationRecord(
        raw_text=raw_text,
        final_text=final_text,
        cleaned_text=cleaned_text,
        app_category=app_category,
        style=style,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    with open(LAST_DICTATION_FILE, "w") as file:
        yaml.safe_dump(asdict(record), file, sort_keys=False)


def load_last_dictation() -> DictationRecord | None:
    """Load the most recent dictation if it exists."""
    if not LAST_DICTATION_FILE.exists():
        return None

    with open(LAST_DICTATION_FILE) as file:
        payload = yaml.safe_load(file) or {}

    try:
        return DictationRecord(
            raw_text=str(payload["raw_text"]),
            final_text=str(payload["final_text"]),
            cleaned_text=str(payload.get("cleaned_text", payload["final_text"])),
            app_category=str(payload.get("app_category", "generic")),
            style=str(payload.get("style", "balanced")),
            timestamp=str(payload.get("timestamp", "")),
        )
    except KeyError:
        return None


def _tokenize(text: str) -> list[str]:
    """Split text into word-ish tokens while keeping punctuation separate."""
    return re.findall(r"[A-Za-z0-9']+|[^\w\s]", text)


def _join_tokens(tokens: list[str]) -> str:
    """Join token spans back into a readable phrase."""
    text = " ".join(tokens).strip()
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    return text.strip()


def _clean_phrase(text: str) -> str:
    """Normalize edge punctuation/spacing on a learned phrase."""
    cleaned = text.strip()
    cleaned = cleaned.strip('.,!?;:()[]{}"')
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def extract_replacement_candidates(original: str, corrected: str) -> list[tuple[str, str]]:
    """Extract replacement candidates from a corrected version of the last dictation."""
    original_tokens = _tokenize(original)
    corrected_tokens = _tokenize(corrected)
    matcher = SequenceMatcher(a=original_tokens, b=corrected_tokens)

    candidates: list[tuple[str, str]] = []
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode != "replace":
            continue

        old_phrase = _clean_phrase(_join_tokens(original_tokens[a0:a1]))
        new_phrase = _clean_phrase(_join_tokens(corrected_tokens[b0:b1]))

        if not old_phrase or not new_phrase:
            continue
        if old_phrase.lower() == new_phrase.lower():
            continue
        if len(old_phrase.split()) > 4 or len(new_phrase.split()) > 4:
            continue

        candidates.append((old_phrase, new_phrase))

    return candidates


def learn_from_correction(original: str, corrected: str) -> dict[str, str]:
    """Build a dictionary mapping from a corrected version of the original text."""
    return dict(extract_replacement_candidates(original, corrected))


def read_text_file(path: str | Path) -> str:
    """Small helper for tests and debugging."""
    with open(path) as file:
        return file.read()
