"""Backward-compatibility shim — re-exports from new modules.

All classes and functions that used to live here have been split into
dedicated modules.  This file keeps ``from undertone.core import X``
working so nothing downstream breaks.
"""

# ruff: noqa: F401  (unused imports are intentional re-exports)

from undertone.audio import AudioRecorder
from undertone.cleanup import (
    CLEANUP_SYSTEM_PROMPT,
    FILLER_PATTERNS,
    TextCleaner,
)
from undertone.engine import UndertoneEngine
from undertone.hotkeys import HotkeyManager, _parse_key
from undertone.injection import (
    _CLIP_COPY,
    _CLIP_PASTE,
    _KEY_TOOL,
    _detect_tools,
    _simulate_paste,
    detect_session,
    inject_text,
)
from undertone.sounds import SoundFeedback
from undertone.transcriber import (
    GroqTranscriber,
    LocalTranscriber,
    route_transcription,
)
from undertone.tray import (
    HAS_TRAY,
    TRAY_COLORS,
    TRAY_TITLES,
    TrayManager,
)

__all__ = [
    "AudioRecorder",
    "CLEANUP_SYSTEM_PROMPT",
    "FILLER_PATTERNS",
    "GroqTranscriber",
    "HAS_TRAY",
    "HotkeyManager",
    "LocalTranscriber",
    "SoundFeedback",
    "TRAY_COLORS",
    "TRAY_TITLES",
    "TextCleaner",
    "TrayManager",
    "UndertoneEngine",
    "_CLIP_COPY",
    "_CLIP_PASTE",
    "_KEY_TOOL",
    "_detect_tools",
    "_parse_key",
    "_simulate_paste",
    "detect_session",
    "inject_text",
    "route_transcription",
]
