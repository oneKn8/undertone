"""Tests for personalized dictation helpers."""

from __future__ import annotations

from undertone.personalization import (
    apply_dictionary_replacements,
    expand_snippet,
    normalize_spoken_text,
    resolve_style,
)


class TestNormalizeSpokenText:
    def test_normalizes_spacing_and_punctuation(self) -> None:
        assert normalize_spoken_text("Yo,   it's working!!") == "yo it's working"


class TestExpandSnippet:
    def test_matches_trigger_ignoring_punctuation(self) -> None:
        snippets = {"my email": "me@example.com"}
        assert expand_snippet("My email.", snippets) == "me@example.com"

    def test_returns_none_for_non_match(self) -> None:
        snippets = {"my email": "me@example.com"}
        assert expand_snippet("not that one", snippets) is None


class TestApplyDictionaryReplacements:
    def test_applies_case_insensitive_replacements(self) -> None:
        replacements = {"grok": "Groq", "repo": "repository"}
        result = apply_dictionary_replacements("grok repo", replacements)
        assert result == "Groq repository"

    def test_prefers_longer_matches_first(self) -> None:
        replacements = {"github repo": "GitHub repository", "repo": "repository"}
        result = apply_dictionary_replacements("github repo", replacements)
        assert result == "GitHub repository"


class TestResolveStyle:
    def test_resolves_auto_from_app_category(self) -> None:
        app_styles = {"chat": "casual", "generic": "balanced"}
        assert resolve_style("auto", app_styles, "chat") == "casual"

    def test_respects_manual_style(self) -> None:
        assert resolve_style("polished", {}, "terminal") == "polished"
