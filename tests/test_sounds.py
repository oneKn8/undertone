"""Tests for sound feedback — beep generation and playback mock."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from undertone.sounds import (
    SoundFeedback,
    _generate_tone,
    _generate_descending_tone,
    _START_BEEP,
    _STOP_BEEP,
    _SAMPLE_RATE,
)


class TestToneGeneration:
    def test_generate_tone_shape(self) -> None:
        tone = _generate_tone(440, 0.1)
        expected_samples = int(_SAMPLE_RATE * 0.1)
        assert len(tone) == expected_samples

    def test_generate_tone_dtype(self) -> None:
        tone = _generate_tone(440, 0.1)
        assert tone.dtype == np.float32

    def test_generate_tone_volume(self) -> None:
        tone = _generate_tone(440, 0.1, volume=0.5)
        assert np.max(np.abs(tone)) <= 0.5 + 0.01  # Small tolerance

    def test_generate_descending_tone_shape(self) -> None:
        tone = _generate_descending_tone(440, 220, 0.15)
        expected_samples = int(_SAMPLE_RATE * 0.15)
        assert len(tone) == expected_samples

    def test_generate_descending_tone_dtype(self) -> None:
        tone = _generate_descending_tone(440, 220, 0.15)
        assert tone.dtype == np.float32

    def test_start_beep_exists(self) -> None:
        assert _START_BEEP is not None
        assert len(_START_BEEP) > 0

    def test_stop_beep_exists(self) -> None:
        assert _STOP_BEEP is not None
        assert len(_STOP_BEEP) > 0


class TestSoundFeedback:
    def test_disabled(self) -> None:
        feedback = SoundFeedback(enabled=False)
        assert feedback.enabled is False
        feedback.play_start()  # Should not raise
        feedback.play_stop()  # Should not raise

    @patch("undertone.sounds.sd", create=True)
    def test_play_start(self, mock_sd: MagicMock) -> None:
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            feedback = SoundFeedback(enabled=True)
            feedback._sd = mock_sd
            feedback._play(_START_BEEP)
            mock_sd.play.assert_called_once()
            mock_sd.wait.assert_called_once()

    @patch("undertone.sounds.sd", create=True)
    def test_play_stop(self, mock_sd: MagicMock) -> None:
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            feedback = SoundFeedback(enabled=True)
            feedback._sd = mock_sd
            feedback._play(_STOP_BEEP)
            mock_sd.play.assert_called_once()

    def test_play_handles_error(self) -> None:
        feedback = SoundFeedback(enabled=True)
        mock_sd = MagicMock()
        mock_sd.play.side_effect = Exception("audio error")
        feedback._sd = mock_sd
        feedback._play(_START_BEEP)  # Should not raise
