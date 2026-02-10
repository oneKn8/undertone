"""Tests for transcription — Groq mock, retry, local mock, routing."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch, PropertyMock

import httpx
import pytest

from undertone.transcriber import (
    GroqTranscriber,
    LocalTranscriber,
    route_transcription,
    _RETRYABLE_STATUSES,
)


# ---------------------------------------------------------------------------
# GroqTranscriber
# ---------------------------------------------------------------------------


class TestGroqTranscriber:
    def test_transcribe_success(self, wav_buffer: io.BytesIO) -> None:
        transcriber = GroqTranscriber(api_key="gsk_test")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "  Hello world  "}
        mock_resp.raise_for_status = MagicMock()

        transcriber._client = MagicMock()
        transcriber._client.post.return_value = mock_resp

        result = transcriber.transcribe(wav_buffer)
        assert result == "Hello world"

    def test_transcribe_no_api_key(self, wav_buffer: io.BytesIO) -> None:
        transcriber = GroqTranscriber(api_key="")
        with pytest.raises(ValueError, match="No Groq API key"):
            transcriber.transcribe(wav_buffer)

    def test_transcribe_sends_language(self, wav_buffer: io.BytesIO) -> None:
        transcriber = GroqTranscriber(api_key="gsk_test", language="en")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"text": "Test"}
        mock_resp.raise_for_status = MagicMock()

        transcriber._client = MagicMock()
        transcriber._client.post.return_value = mock_resp

        transcriber.transcribe(wav_buffer)
        call_kwargs = transcriber._client.post.call_args
        assert "language" in call_kwargs.kwargs.get("data", {})

    def test_close(self) -> None:
        transcriber = GroqTranscriber(api_key="gsk_test")
        transcriber._client = MagicMock()
        transcriber.close()
        transcriber._client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Retry behavior
# ---------------------------------------------------------------------------


class TestRetryBehavior:
    @pytest.mark.parametrize("status_code", [429, 500, 502, 503])
    def test_retries_on_retryable_status(
        self, wav_buffer: io.BytesIO, status_code: int
    ) -> None:
        transcriber = GroqTranscriber(api_key="gsk_test")

        # First call returns retryable status, second succeeds
        fail_resp = MagicMock()
        fail_resp.status_code = status_code

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"text": "Success"}
        ok_resp.raise_for_status = MagicMock()

        transcriber._client = MagicMock()
        transcriber._client.post.side_effect = [fail_resp, ok_resp]

        with patch("undertone.transcriber.time.sleep"):
            result = transcriber.transcribe(wav_buffer)

        assert result == "Success"
        assert transcriber._client.post.call_count == 2

    def test_no_retry_on_401(self, wav_buffer: io.BytesIO) -> None:
        transcriber = GroqTranscriber(api_key="gsk_test")

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_resp
        )

        transcriber._client = MagicMock()
        transcriber._client.post.return_value = mock_resp

        with pytest.raises(httpx.HTTPStatusError):
            transcriber.transcribe(wav_buffer)

        assert transcriber._client.post.call_count == 1  # No retry

    def test_retries_on_timeout(self, wav_buffer: io.BytesIO) -> None:
        transcriber = GroqTranscriber(api_key="gsk_test")

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"text": "After retry"}
        ok_resp.raise_for_status = MagicMock()

        transcriber._client = MagicMock()
        transcriber._client.post.side_effect = [
            httpx.TimeoutException("timeout"),
            ok_resp,
        ]

        with patch("undertone.transcriber.time.sleep"):
            result = transcriber.transcribe(wav_buffer)

        assert result == "After retry"

    def test_max_retries_exceeded(self, wav_buffer: io.BytesIO) -> None:
        transcriber = GroqTranscriber(api_key="gsk_test")

        fail_resp = MagicMock()
        fail_resp.status_code = 500
        fail_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=fail_resp
        )

        transcriber._client = MagicMock()
        transcriber._client.post.return_value = fail_resp

        with patch("undertone.transcriber.time.sleep"):
            with pytest.raises(httpx.HTTPStatusError):
                transcriber.transcribe(wav_buffer)

        assert transcriber._client.post.call_count == 3  # 1 + 2 retries


# ---------------------------------------------------------------------------
# LocalTranscriber
# ---------------------------------------------------------------------------


class TestLocalTranscriber:
    def test_preload(self) -> None:
        transcriber = LocalTranscriber(model_size="tiny")
        with patch("undertone.transcriber.WhisperModel", create=True) as mock_cls:
            # Patch the import inside the method
            with patch.dict(
                "sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_cls)}
            ):
                transcriber.preload()
        assert transcriber._model is not None

    def test_preload_only_once(self) -> None:
        transcriber = LocalTranscriber()
        transcriber._model = MagicMock()  # Already loaded
        transcriber.preload()  # Should not reload


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


class TestRouteTranscription:
    def test_routes_to_groq(self, wav_buffer: io.BytesIO) -> None:
        groq = MagicMock()
        groq.api_key = "gsk_test"
        groq.transcribe.return_value = "Groq result"

        local = MagicMock()
        config = {"stt": {"primary": "groq"}}

        text, source = route_transcription(wav_buffer, groq, local, config)
        assert text == "Groq result"
        assert source == "groq"
        local.transcribe.assert_not_called()

    def test_falls_back_to_local(self, wav_buffer: io.BytesIO) -> None:
        groq = MagicMock()
        groq.api_key = "gsk_test"
        groq.transcribe.side_effect = Exception("API error")

        local = MagicMock()
        local.transcribe.return_value = "Local result"
        config = {"stt": {"primary": "groq"}}

        text, source = route_transcription(wav_buffer, groq, local, config)
        assert text == "Local result"
        assert source == "local"

    def test_uses_local_when_configured(self, wav_buffer: io.BytesIO) -> None:
        groq = MagicMock()
        groq.api_key = "gsk_test"

        local = MagicMock()
        local.transcribe.return_value = "Local only"
        config = {"stt": {"primary": "local"}}

        text, source = route_transcription(wav_buffer, groq, local, config)
        assert text == "Local only"
        assert source == "local"
        groq.transcribe.assert_not_called()

    def test_uses_local_when_no_api_key(self, wav_buffer: io.BytesIO) -> None:
        groq = MagicMock()
        groq.api_key = ""

        local = MagicMock()
        local.transcribe.return_value = "Local fallback"
        config = {"stt": {"primary": "groq"}}

        text, source = route_transcription(wav_buffer, groq, local, config)
        assert text == "Local fallback"
        assert source == "local"
