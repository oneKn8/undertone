"""Display-session detection and clipboard-based text injection."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time

log = logging.getLogger("undertone")


def detect_session() -> str:
    """Detect display server: 'wayland' or 'x11'."""
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session in ("wayland", "x11"):
        return session
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "x11"


def _detect_tools() -> tuple[list[str], list[str], str]:
    """Pick the right clipboard and key simulation tools for the session."""
    session = detect_session()

    if session == "wayland":
        # Clipboard: prefer wl-copy, fall back to xclip (works via XWayland)
        if shutil.which("wl-copy"):
            clip_copy = ["wl-copy"]
            clip_paste = ["wl-paste", "--no-newline"]
        else:
            clip_copy = ["xclip", "-sel", "clip"]
            clip_paste = ["xclip", "-sel", "clip", "-o"]

        # Key simulation: prefer wtype (fast), then ydotool, then xdotool
        if shutil.which("wtype"):
            key_tool = "wtype"
        elif shutil.which("ydotool"):
            key_tool = "ydotool"
        else:
            key_tool = "xdotool"
    else:
        clip_copy = ["xclip", "-sel", "clip"]
        clip_paste = ["xclip", "-sel", "clip", "-o"]
        key_tool = "xdotool"

    return clip_copy, clip_paste, key_tool


# Cache detected tools at module level (session doesn't change mid-run)
_CLIP_COPY, _CLIP_PASTE, _KEY_TOOL = _detect_tools()


def _simulate_paste() -> None:
    """Simulate Ctrl+V using the appropriate tool for the session."""
    if _KEY_TOOL == "wtype":
        subprocess.run(["wtype", "-M", "ctrl", "v", "-m", "ctrl"], timeout=2)
    elif _KEY_TOOL == "ydotool":
        # Raw keycodes: 29=KEY_LEFTCTRL, 47=KEY_V
        subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], timeout=2)
    else:
        subprocess.run(["xdotool", "key", "ctrl+v"], timeout=2)


def inject_text(text: str, restore_clipboard: bool = True) -> None:
    """Type text at cursor position via clipboard paste."""
    if not text:
        return

    old_clipboard: bytes | None = None
    if restore_clipboard:
        try:
            result = subprocess.run(
                _CLIP_PASTE,
                capture_output=True,
                timeout=1.0,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                old_clipboard = result.stdout
        except Exception:
            pass

    proc = subprocess.Popen(
        _CLIP_COPY,
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    proc.communicate(text.encode("utf-8"))

    time.sleep(0.05)
    _simulate_paste()
    time.sleep(0.15)  # Increased from 100ms to 150ms

    if restore_clipboard and old_clipboard is not None:
        time.sleep(0.1)
        proc = subprocess.Popen(
            _CLIP_COPY,
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(old_clipboard)
