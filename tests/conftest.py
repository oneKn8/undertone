"""Shared fixtures for Undertone tests."""

from __future__ import annotations

import io
import wave
from unittest.mock import MagicMock

import numpy as np
import pytest


@pytest.fixture
def mock_config() -> dict:
    """Standard test configuration."""
    return {
        "stt": {
            "primary": "groq",
            "groq_model": "whisper-large-v3-turbo",
            "local_model": "distil-large-v3",
            "local_device": "cpu",
            "local_compute_type": "int8",
            "language": "en",
        },
        "cleanup": {
            "enabled": True,
            "llm_enabled": True,
            "model": "llama-3.1-8b-instant",
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "sound_feedback": False,
            "pre_buffer_seconds": 0.5,
        },
        "hotkeys": {
            "push_to_talk": "Key.ctrl_r",
            "toggle": "Key.f8",
        },
        "text_injection": {
            "method": "clipboard",
            "restore_clipboard": True,
        },
        "tray": {
            "enabled": False,
        },
    }


@pytest.fixture
def fake_api_key() -> str:
    """Fake Groq API key for testing."""
    return "gsk_test1234567890abcdef"


@pytest.fixture
def wav_buffer() -> io.BytesIO:
    """Generate a valid 1-second WAV buffer with silence."""
    sample_rate = 16000
    duration = 1.0
    samples = np.zeros(int(sample_rate * duration), dtype=np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    buf.seek(0)
    return buf


@pytest.fixture
def mock_httpx_client() -> MagicMock:
    """Mock httpx.Client for API tests."""
    return MagicMock()
