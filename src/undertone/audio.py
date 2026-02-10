"""Audio recording with rolling pre-buffer."""

from __future__ import annotations

import io
import logging
import threading
import wave
from collections import deque
from typing import Optional

import numpy as np
import sounddevice as sd

log = logging.getLogger("undertone")


class AudioRecorder:
    """Captures microphone audio with a rolling pre-buffer."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        pre_buffer_sec: float = 0.5,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = 1024
        pre_buffer_chunks = int(sample_rate * pre_buffer_sec / self.chunk_size)
        self.pre_buffer: deque[np.ndarray] = deque(maxlen=max(pre_buffer_chunks, 1))
        self.recording_chunks: list[np.ndarray] = []
        self.is_recording = False
        self.stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

    def open(self) -> None:
        """Start the always-on audio input stream for pre-buffering."""
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self.chunk_size,
            callback=self._audio_callback,
        )
        self.stream.start()

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        chunk = indata.copy()
        with self._lock:
            if self.is_recording:
                self.recording_chunks.append(chunk)
            else:
                self.pre_buffer.append(chunk)

    def start_recording(self) -> None:
        """Begin capturing audio, including the pre-buffer."""
        with self._lock:
            self.recording_chunks = list(self.pre_buffer)
            self.pre_buffer.clear()
            self.is_recording = True
        log.info("Recording started")

    def stop_recording(self) -> Optional[io.BytesIO]:
        """Stop capturing and return audio as an in-memory WAV BytesIO."""
        with self._lock:
            self.is_recording = False
            chunks = self.recording_chunks
            self.recording_chunks = []

        if not chunks:
            log.warning("No audio captured")
            return None

        audio_data = np.concatenate(chunks, axis=0)
        duration = len(audio_data) / self.sample_rate
        log.info(f"Captured {duration:.1f}s of audio")

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
        buf.seek(0)
        return buf

    def close(self) -> None:
        """Stop and close the audio stream."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
