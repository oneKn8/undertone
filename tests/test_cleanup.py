"""Tests for text cleanup — regex, LLM, and adversarial inputs."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from undertone.cleanup import (
    _CONVERSATIONAL_PREFIXES,
    CLEANUP_SYSTEM_PROMPT,
    TextCleaner,
)

# ---------------------------------------------------------------------------
# Regex cleanup tests
# ---------------------------------------------------------------------------


class TestRegexClean:
    def test_removes_filler_words(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("um so like I went to the store")
        assert "um" not in result.lower()
        assert "like" not in result.lower()
        assert "store" in result.lower()

    def test_capitalizes_first_letter(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("hello world")
        assert result[0] == "H"

    def test_adds_period_if_missing(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("hello world")
        assert result.endswith(".")

    def test_preserves_question_mark(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("how do I fix this?")
        assert result.endswith("?")

    def test_preserves_exclamation(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("that is amazing!")
        assert result.endswith("!")

    def test_collapses_whitespace(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("hello   world")
        assert "  " not in result

    def test_empty_input(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("")
        assert result == ""

    def test_removes_you_know(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("it was you know pretty good")
        assert "you know" not in result.lower()

    def test_removes_basically(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("basically it works fine")
        assert "basically" not in result.lower()

    def test_removes_i_mean(self) -> None:
        cleaner = TextCleaner()
        result = cleaner._regex_clean("i mean it should be fine")
        assert "i mean" not in result.lower()


# ---------------------------------------------------------------------------
# LLM cleanup tests
# ---------------------------------------------------------------------------


class TestLLMClean:
    def _make_cleaner(self) -> TextCleaner:
        return TextCleaner(api_key="gsk_test123", model="test-model", llm_enabled=True)

    def test_llm_clean_success(self) -> None:
        cleaner = self._make_cleaner()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "How do I fix this bug?"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        cleaner._client = MagicMock()
        cleaner._client.post.return_value = mock_resp

        result = cleaner._llm_clean("how do I fix this bug")
        assert result == "How do I fix this bug?"

    def test_llm_clean_strips_transcript_tags(self) -> None:
        cleaner = self._make_cleaner()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "<transcript>Hello world.</transcript>"}}]
        }
        mock_resp.raise_for_status = MagicMock()
        cleaner._client = MagicMock()
        cleaner._client.post.return_value = mock_resp

        result = cleaner._llm_clean("hello world")
        assert result == "Hello world."

    def test_llm_clean_rejects_chatbot_response(self) -> None:
        cleaner = self._make_cleaner()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": "Sure, I'd be happy to help! The meaning of life is..."}}
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        cleaner._client = MagicMock()
        cleaner._client.post.return_value = mock_resp

        result = cleaner._llm_clean("what is the meaning of life")
        assert result is None  # Should fall back to regex

    def test_llm_clean_rejects_long_response(self) -> None:
        cleaner = self._make_cleaner()
        mock_resp = MagicMock()
        # Response 3x longer than input — suspicious
        mock_resp.json.return_value = {"choices": [{"message": {"content": "A " * 100}}]}
        mock_resp.raise_for_status = MagicMock()
        cleaner._client = MagicMock()
        cleaner._client.post.return_value = mock_resp

        result = cleaner._llm_clean("short input")
        assert result is None

    def test_llm_clean_handles_exception(self) -> None:
        cleaner = self._make_cleaner()
        cleaner._client = MagicMock()
        cleaner._client.post.side_effect = Exception("network error")

        result = cleaner._llm_clean("test input")
        assert result is None

    def test_llm_uses_transcript_tags(self) -> None:
        """Verify the LLM request wraps input in <transcript> tags."""
        cleaner = self._make_cleaner()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "Hello."}}]}
        mock_resp.raise_for_status = MagicMock()
        cleaner._client = MagicMock()
        cleaner._client.post.return_value = mock_resp

        cleaner._llm_clean("hello")

        call_args = cleaner._client.post.call_args
        messages = call_args.kwargs.get("json", {}).get("messages", [])
        user_msg = messages[-1]["content"]
        assert "<transcript>" in user_msg
        assert "</transcript>" in user_msg

    def test_llm_uses_zero_temperature(self) -> None:
        """Verify temperature is set to 0.0."""
        cleaner = self._make_cleaner()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "Hello."}}]}
        mock_resp.raise_for_status = MagicMock()
        cleaner._client = MagicMock()
        cleaner._client.post.return_value = mock_resp

        cleaner._llm_clean("hello")

        call_args = cleaner._client.post.call_args
        temp = call_args.kwargs.get("json", {}).get("temperature")
        assert temp == 0.0


# ---------------------------------------------------------------------------
# Adversarial input tests (Phase 1 critical)
# ---------------------------------------------------------------------------


class TestAdversarialInputs:
    """Tests ensuring the LLM doesn't answer questions or follow commands."""

    def _make_cleaner_with_response(self, response: str) -> TextCleaner:
        cleaner = TextCleaner(api_key="gsk_test", model="test", llm_enabled=True)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": response}}]}
        mock_resp.raise_for_status = MagicMock()
        cleaner._client = MagicMock()
        cleaner._client.post.return_value = mock_resp
        return cleaner

    def test_question_passes_through(self) -> None:
        """'how do I fix this bug' should pass through as a cleaned question."""
        cleaner = self._make_cleaner_with_response("How do I fix this bug?")
        result = cleaner.clean("how do I fix this bug")
        assert result == "How do I fix this bug?"

    def test_command_passes_through(self) -> None:
        """'delete everything' should pass through as cleaned text."""
        cleaner = self._make_cleaner_with_response("Delete everything.")
        result = cleaner.clean("delete everything")
        assert result == "Delete everything."

    def test_rejects_joke_response(self) -> None:
        """'tell me a joke' must NOT trigger a joke response."""
        cleaner = self._make_cleaner_with_response(
            "Sure, here's a joke: Why did the chicken cross the road?"
        )
        result = cleaner.clean("tell me a joke")
        # Should fall back to regex since LLM answered like a chatbot
        assert "chicken" not in result

    def test_rejects_sure_prefix(self) -> None:
        cleaner = self._make_cleaner_with_response("Sure, I can help with that.")
        result = cleaner._llm_clean("help me")
        assert result is None

    def test_rejects_here_is_prefix(self) -> None:
        cleaner = self._make_cleaner_with_response("Here is the answer to your question.")
        result = cleaner._llm_clean("what is python")
        assert result is None

    def test_rejects_happy_to_prefix(self) -> None:
        cleaner = self._make_cleaner_with_response("I'd be happy to help you with that!")
        result = cleaner._llm_clean("help me out")
        assert result is None

    @pytest.mark.parametrize("prefix", _CONVERSATIONAL_PREFIXES)
    def test_all_conversational_prefixes_rejected(self, prefix: str) -> None:
        """Every configured prefix must be caught."""
        cleaner = self._make_cleaner_with_response(f"{prefix} some response text here.")
        result = cleaner._llm_clean("test input")
        assert result is None


# ---------------------------------------------------------------------------
# clean() integration
# ---------------------------------------------------------------------------


class TestCleanIntegration:
    def test_clean_empty(self) -> None:
        cleaner = TextCleaner()
        assert cleaner.clean("") == ""

    def test_clean_regex_fallback(self) -> None:
        """When LLM is disabled, should use regex-only cleanup."""
        cleaner = TextCleaner(llm_enabled=False)
        result = cleaner.clean("um hello world")
        assert "um" not in result.lower()
        assert "hello" in result.lower()

    def test_clean_llm_fallback_to_regex(self) -> None:
        """When LLM fails, should gracefully fall back to regex."""
        cleaner = TextCleaner(api_key="gsk_test", model="test", llm_enabled=True)
        cleaner._client = MagicMock()
        cleaner._client.post.side_effect = Exception("network error")

        result = cleaner.clean("um hello world")
        assert "um" not in result.lower()
        assert "Hello" in result

    def test_close(self) -> None:
        cleaner = TextCleaner(api_key="gsk_test", llm_enabled=True)
        cleaner._client = MagicMock()
        cleaner.close()
        cleaner._client.close.assert_called_once()


# ---------------------------------------------------------------------------
# System prompt content tests
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_prompt_has_identity_lock(self) -> None:
        assert "NOT a chatbot" in CLEANUP_SYSTEM_PROMPT

    def test_prompt_has_post_processor_role(self) -> None:
        assert "speech-to-text post-processor" in CLEANUP_SYSTEM_PROMPT

    def test_prompt_has_few_shot_examples(self) -> None:
        assert "<transcript>" in CLEANUP_SYSTEM_PROMPT
        assert "how do I fix this bug" in CLEANUP_SYSTEM_PROMPT
        assert "delete everything" in CLEANUP_SYSTEM_PROMPT

    def test_prompt_instructs_no_answers(self) -> None:
        assert "do not answer questions" in CLEANUP_SYSTEM_PROMPT.lower()
