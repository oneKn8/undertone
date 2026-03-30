"""Tests for last-dictation storage and correction learning."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from undertone.learning import (
    DictationRecord,
    extract_replacement_candidates,
    learn_from_correction,
    load_last_dictation,
    save_last_dictation,
)


class TestLearnFromCorrection:
    def test_extracts_simple_name_fix(self) -> None:
        learned = learn_from_correction("I met jon yesterday.", "I met John yesterday.")
        assert learned == {"jon": "John"}

    def test_extracts_repo_name_fix(self) -> None:
        learned = learn_from_correction("push it to get hub", "push it to GitHub")
        assert learned == {"get hub": "GitHub"}

    def test_ignores_big_sentence_rewrites(self) -> None:
        candidates = extract_replacement_candidates(
            "this is fine",
            "I rewrote the whole sentence into something completely different",
        )
        assert candidates == []


class TestLastDictationStorage:
    def test_round_trips_last_dictation(self, tmp_path: Path) -> None:
        state_file = tmp_path / "last_dictation.yaml"

        with patch("undertone.learning.LAST_DICTATION_FILE", state_file):
            save_last_dictation(
                raw_text="jon",
                final_text="jon",
                cleaned_text="jon",
                app_category="chat",
                style="casual",
            )
            loaded = load_last_dictation()

        assert loaded == DictationRecord(
            raw_text="jon",
            final_text="jon",
            cleaned_text="jon",
            app_category="chat",
            style="casual",
            timestamp=loaded.timestamp if loaded else "",
        )
