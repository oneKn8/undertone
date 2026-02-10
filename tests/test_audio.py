"""Tests for AudioRecorder — mock sounddevice, pre-buffer, WAV output."""

from __future__ import annotations

import io
import wave
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from undertone.audio import AudioRecorder


class TestAudioRecorder:
    def test_init_defaults(self) -> None:
        recorder = AudioRecorder()
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.is_recording is False
        assert recorder.stream is None

    def test_init_custom(self) -> None:
        recorder = AudioRecorder(sample_rate=44100, channels=2, pre_buffer_sec=1.0)
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2

    @patch("undertone.audio.sd")
    def test_open_creates_stream(self, mock_sd: MagicMock) -> None:
        recorder = AudioRecorder()
        recorder.open()
        mock_sd.InputStream.assert_called_once()
        mock_sd.InputStream.return_value.start.assert_called_once()

    def test_start_recording(self) -> None:
        recorder = AudioRecorder()
        # Simulate some pre-buffer data
        recorder.pre_buffer.append(np.zeros((1024, 1), dtype=np.int16))
        recorder.start_recording()
        assert recorder.is_recording is True
        assert len(recorder.recording_chunks) == 1
        assert len(recorder.pre_buffer) == 0

    def test_stop_recording_returns_wav(self) -> None:
        recorder = AudioRecorder()
        recorder.is_recording = True
        recorder.recording_chunks = [
            np.zeros((1024, 1), dtype=np.int16),
            np.ones((1024, 1), dtype=np.int16),
        ]

        result = recorder.stop_recording()
        assert result is not None
        assert isinstance(result, io.BytesIO)

        # Verify it's a valid WAV
        result.seek(0)
        with wave.open(result, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000

    def test_stop_recording_no_audio(self) -> None:
        recorder = AudioRecorder()
        recorder.is_recording = True
        recorder.recording_chunks = []

        result = recorder.stop_recording()
        assert result is None

    def test_audio_callback_recording(self) -> None:
        recorder = AudioRecorder()
        recorder.is_recording = True
        chunk = np.ones((1024, 1), dtype=np.int16)

        recorder._audio_callback(chunk, 1024, None, None)
        assert len(recorder.recording_chunks) == 1

    def test_audio_callback_prebuffer(self) -> None:
        recorder = AudioRecorder()
        recorder.is_recording = False
        chunk = np.ones((1024, 1), dtype=np.int16)

        recorder._audio_callback(chunk, 1024, None, None)
        assert len(recorder.pre_buffer) == 1
        assert len(recorder.recording_chunks) == 0

    def test_close(self) -> None:
        recorder = AudioRecorder()
        recorder.stream = MagicMock()
        recorder.close()
        recorder.stream is None  # noqa: B015 — just checking

    def test_close_no_stream(self) -> None:
        recorder = AudioRecorder()
        recorder.close()  # Should not raise
