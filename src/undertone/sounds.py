"""Audio feedback beeps for recording start/stop."""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np

log = logging.getLogger("undertone")

# Pre-generated beep arrays (created once at import time)
_SAMPLE_RATE = 44100


def _generate_tone(
    frequency: float,
    duration: float,
    sample_rate: int = _SAMPLE_RATE,
    volume: float = 0.3,
) -> np.ndarray:
    """Generate a sine wave tone as a float32 numpy array."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone = (volume * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    # Apply fade-in/out to avoid clicks (5ms)
    fade_samples = int(sample_rate * 0.005)
    if fade_samples > 0 and len(tone) > 2 * fade_samples:
        fade_in = np.linspace(0, 1, fade_samples, dtype=np.float32)
        fade_out = np.linspace(1, 0, fade_samples, dtype=np.float32)
        tone[:fade_samples] *= fade_in
        tone[-fade_samples:] *= fade_out
    return tone


def _generate_descending_tone(
    freq_start: float,
    freq_end: float,
    duration: float,
    sample_rate: int = _SAMPLE_RATE,
    volume: float = 0.3,
) -> np.ndarray:
    """Generate a descending frequency sweep."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    freqs = np.linspace(freq_start, freq_end, len(t))
    phase = np.cumsum(2 * np.pi * freqs / sample_rate)
    tone = (volume * np.sin(phase)).astype(np.float32)
    # Fade
    fade_samples = int(sample_rate * 0.005)
    if fade_samples > 0 and len(tone) > 2 * fade_samples:
        fade_in = np.linspace(0, 1, fade_samples, dtype=np.float32)
        fade_out = np.linspace(1, 0, fade_samples, dtype=np.float32)
        tone[:fade_samples] *= fade_in
        tone[-fade_samples:] *= fade_out
    return tone


# Pre-generate beep arrays
_START_BEEP = _generate_tone(880, 0.1)
_STOP_BEEP = _generate_descending_tone(440, 220, 0.15)


class SoundFeedback:
    """Non-blocking audio feedback for recording events."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._sd: Optional[object] = None
        if enabled:
            try:
                import sounddevice as sd

                self._sd = sd
            except Exception:
                log.warning("sounddevice not available, disabling sound feedback")
                self.enabled = False

    def play_start(self) -> None:
        """Play the recording-start beep (880Hz, 100ms)."""
        if not self.enabled:
            return
        self._play_async(_START_BEEP)

    def play_stop(self) -> None:
        """Play the recording-stop beep (440→220Hz descending, 150ms)."""
        if not self.enabled:
            return
        self._play_async(_STOP_BEEP)

    def _play_async(self, audio: np.ndarray) -> None:
        """Play audio in a daemon thread to avoid blocking."""
        thread = threading.Thread(target=self._play, args=(audio,), daemon=True)
        thread.start()

    def _play(self, audio: np.ndarray) -> None:
        """Play audio synchronously."""
        try:
            sd = self._sd
            sd.play(audio, samplerate=_SAMPLE_RATE)  # type: ignore[union-attr]
            sd.wait()  # type: ignore[union-attr]
        except Exception as e:
            log.debug(f"Sound playback failed: {e}")
