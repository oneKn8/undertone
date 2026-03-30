"""Tests for UndertoneEngine — integration test with full pipeline mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestUndertoneEngine:
    def _make_engine(self, config: dict) -> object:
        with (
            patch("undertone.engine.AudioRecorder"),
            patch("undertone.engine.GroqTranscriber"),
            patch("undertone.engine.LocalTranscriber"),
            patch("undertone.engine.TextCleaner"),
            patch("undertone.engine.HotkeyManager"),
            patch("undertone.engine.SoundFeedback"),
            patch("undertone.engine.HAS_TRAY", False),
        ):
            from undertone.engine import UndertoneEngine

            engine = UndertoneEngine(config, api_key="gsk_test")
            return engine

    def test_init_creates_components(self, mock_config: dict) -> None:
        engine = self._make_engine(mock_config)
        assert engine.api_key == "gsk_test"
        assert engine._recording is False
        assert engine._transcribing is False

    def test_on_record_start(self, mock_config: dict) -> None:
        engine = self._make_engine(mock_config)
        engine._on_record_start()
        assert engine._recording is True
        engine.recorder.start_recording.assert_called_once()
        engine.sounds.play_start.assert_called_once()

    def test_on_record_start_ignores_if_already_recording(self, mock_config: dict) -> None:
        engine = self._make_engine(mock_config)
        engine._recording = True
        engine._on_record_start()
        engine.recorder.start_recording.assert_not_called()

    def test_on_record_start_ignores_if_transcribing(self, mock_config: dict) -> None:
        engine = self._make_engine(mock_config)
        engine._transcribing = True
        engine._on_record_start()
        engine.recorder.start_recording.assert_not_called()

    def test_on_record_stop(self, mock_config: dict) -> None:
        engine = self._make_engine(mock_config)
        engine._recording = True
        engine.recorder.stop_recording.return_value = MagicMock()

        with patch.object(engine, "_transcribe_and_type"):
            engine._on_record_stop()

        assert engine._recording is False
        engine.sounds.play_stop.assert_called_once()

    def test_on_record_stop_ignores_if_not_recording(self, mock_config: dict) -> None:
        engine = self._make_engine(mock_config)
        engine._recording = False
        engine._on_record_stop()
        engine.recorder.stop_recording.assert_not_called()

    def test_on_record_stop_no_audio(self, mock_config: dict) -> None:
        engine = self._make_engine(mock_config)
        engine._recording = True
        engine.recorder.stop_recording.return_value = None
        engine._on_record_stop()
        assert engine._transcribing is False

    @patch("undertone.engine.inject_text")
    @patch("undertone.engine.save_last_dictation")
    @patch(
        "undertone.engine.get_focused_app_context",
        return_value={"category": "chat", "signature": "discord"},
    )
    @patch("undertone.engine.route_transcription")
    def test_transcribe_and_type(
        self,
        mock_route: MagicMock,
        mock_save_last: MagicMock,
        mock_context: MagicMock,
        mock_inject: MagicMock,
        mock_config: dict,
    ) -> None:
        mock_route.return_value = ("hello world", "groq")

        engine = self._make_engine(mock_config)
        engine.cleaner = MagicMock()
        engine.cleaner.clean.return_value = "Hello world."

        audio_buf = MagicMock()
        engine._transcribe_and_type(audio_buf)

        engine.cleaner.clean.assert_called_once_with(
            "hello world",
            style="casual",
            app_context="chat",
        )
        mock_save_last.assert_called_once()
        mock_inject.assert_called_once()

    @patch("undertone.engine.inject_text")
    @patch("undertone.engine.save_last_dictation")
    @patch(
        "undertone.engine.get_focused_app_context",
        return_value={"category": "generic", "signature": ""},
    )
    @patch("undertone.engine.route_transcription")
    def test_transcribe_and_type_handles_error(
        self,
        mock_route: MagicMock,
        mock_save_last: MagicMock,
        mock_context: MagicMock,
        mock_inject: MagicMock,
        mock_config: dict,
    ) -> None:
        mock_route.side_effect = Exception("API error")

        engine = self._make_engine(mock_config)
        engine._transcribing = True

        audio_buf = MagicMock()
        engine._transcribe_and_type(audio_buf)

        assert engine._transcribing is False
        mock_inject.assert_not_called()

    @patch("undertone.engine.inject_text")
    @patch("undertone.engine.save_last_dictation")
    @patch(
        "undertone.engine.get_focused_app_context",
        return_value={"category": "generic", "signature": ""},
    )
    @patch("undertone.engine.route_transcription")
    def test_transcribe_and_type_expands_snippet(
        self,
        mock_route: MagicMock,
        mock_context: MagicMock,
        mock_save_last: MagicMock,
        mock_inject: MagicMock,
        mock_config: dict,
    ) -> None:
        mock_route.return_value = ("my email", "groq")
        mock_config["snippets"]["items"] = {"my email": "me@example.com"}

        engine = self._make_engine(mock_config)
        engine.cleaner = MagicMock()

        audio_buf = MagicMock()
        engine._transcribe_and_type(audio_buf)

        engine.cleaner.clean.assert_not_called()
        mock_save_last.assert_called_once()
        mock_inject.assert_called_once()
        assert mock_inject.call_args.args[0] == "me@example.com"

    def test_shutdown(self, mock_config: dict) -> None:
        engine = self._make_engine(mock_config)
        engine.cleaner = MagicMock()

        with pytest.raises(SystemExit):
            engine.shutdown()

        engine.hotkeys.stop.assert_called_once()
        engine.recorder.close.assert_called_once()
        engine.groq.close.assert_called_once()
        engine.cleaner.close.assert_called_once()
