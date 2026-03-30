"""Display-session detection and clipboard-based text injection."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time

log = logging.getLogger("undertone")

_TERMINAL_WINDOW_MARKERS = (
    "alacritty",
    "ghostty",
    "gnome-terminal",
    "guake",
    "hyper",
    "kgx",
    "kitty",
    "konsole",
    "ptyxis",
    "rio",
    "tabby",
    "terminal",
    "terminator",
    "tilix",
    "tmux",
    "warp",
    "wezterm",
    "xterm",
)

_CODE_EDITOR_WINDOW_MARKERS = (
    "code",
    "codium",
    "cursor",
    "windsurf",
    "zed",
    "jetbrains",
    "pycharm",
    "webstorm",
    "clion",
    "goland",
    "idea",
    "nvim",
    "neovim",
    "sublime",
)

_CHAT_WINDOW_MARKERS = (
    "discord",
    "slack",
    "telegram",
    "signal",
    "whatsapp",
    "teams",
    "zulip",
    "element",
    "mattermost",
)

_EMAIL_WINDOW_MARKERS = (
    "thunderbird",
    "outlook",
    "superhuman",
    "proton mail",
    "gmail",
    "mail",
)

_DOC_WINDOW_MARKERS = (
    "docs",
    "notion",
    "obsidian",
    "writer",
    "word",
    "confluence",
    "notes",
)

_BROWSER_WINDOW_MARKERS = (
    "firefox",
    "chrome",
    "chromium",
    "brave",
    "edge",
    "opera",
    "zen",
)


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


def _normalize_paste_shortcut(paste_shortcut: str) -> str:
    """Normalize a paste shortcut setting to an internal value."""
    normalized = paste_shortcut.strip().lower().replace("+", "_").replace("-", "_")
    normalized = normalized.replace(" ", "_")

    if normalized in {"", "auto", "automatic"}:
        return "auto"
    if normalized in {"ctrl_v", "ctrl"}:
        return "ctrl_v"
    if normalized in {"ctrl_shift_v", "terminal"}:
        return "ctrl_shift_v"
    return "auto"


def _run_window_query(command: list[str]) -> str:
    """Run a window query command and return trimmed text output."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            text=True,
            timeout=1.0,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return ""

    if result.returncode != 0:
        return ""

    return result.stdout.strip()


def _get_focused_window_signature() -> str:
    """Return a lowercased string describing the focused X11 window."""
    if _KEY_TOOL != "xdotool":
        return ""

    window_id = _run_window_query(["xdotool", "getwindowfocus"])
    if not window_id:
        return ""

    parts: list[str] = []
    window_name = _run_window_query(["xdotool", "getwindowname", window_id])
    if window_name:
        parts.append(window_name.lower())

    if shutil.which("xprop"):
        window_class = _run_window_query(["xprop", "-id", window_id, "WM_CLASS"])
        if window_class:
            parts.append(window_class.lower())

    return " ".join(parts)


def _looks_like_terminal_window(signature: str) -> bool:
    """Check whether the focused window appears to be a terminal."""
    lowered = signature.lower()
    return any(marker in lowered for marker in _TERMINAL_WINDOW_MARKERS)


def categorize_window_signature(signature: str) -> str:
    """Map a window signature to a coarse app category."""
    lowered = signature.lower()
    if not lowered:
        return "generic"
    if any(marker in lowered for marker in _TERMINAL_WINDOW_MARKERS):
        return "terminal"
    if any(marker in lowered for marker in _CODE_EDITOR_WINDOW_MARKERS):
        return "code_editor"
    if any(marker in lowered for marker in _CHAT_WINDOW_MARKERS):
        return "chat"
    if any(marker in lowered for marker in _EMAIL_WINDOW_MARKERS):
        return "email"
    if any(marker in lowered for marker in _DOC_WINDOW_MARKERS):
        return "docs"
    if any(marker in lowered for marker in _BROWSER_WINDOW_MARKERS):
        return "browser"
    return "generic"


def get_focused_app_context() -> dict[str, str]:
    """Return the focused window signature and coarse app category."""
    signature = _get_focused_window_signature()
    return {
        "signature": signature,
        "category": categorize_window_signature(signature),
    }


def _resolve_paste_shortcut(paste_shortcut: str) -> str:
    """Resolve auto mode to a concrete shortcut."""
    normalized = _normalize_paste_shortcut(paste_shortcut)
    if normalized != "auto":
        return normalized

    signature = _get_focused_window_signature()
    if signature and _looks_like_terminal_window(signature):
        log.info("Terminal window detected; using Ctrl+Shift+V for paste")
        return "ctrl_shift_v"

    return "ctrl_v"


def _simulate_paste(paste_shortcut: str = "auto") -> None:
    """Simulate a paste keystroke using the appropriate tool for the session."""
    shortcut = _resolve_paste_shortcut(paste_shortcut)

    if _KEY_TOOL == "wtype":
        if shortcut == "ctrl_shift_v":
            subprocess.run(
                ["wtype", "-M", "ctrl", "-M", "shift", "v", "-m", "shift", "-m", "ctrl"],
                timeout=2,
            )
        else:
            subprocess.run(["wtype", "-M", "ctrl", "v", "-m", "ctrl"], timeout=2)
    elif _KEY_TOOL == "ydotool":
        if shortcut == "ctrl_shift_v":
            subprocess.run(
                ["ydotool", "key", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"],
                timeout=2,
            )
        else:
            # Raw keycodes: 29=KEY_LEFTCTRL, 47=KEY_V
            subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], timeout=2)
    else:
        combo = "ctrl+shift+v" if shortcut == "ctrl_shift_v" else "ctrl+v"
        subprocess.run(["xdotool", "key", combo], timeout=2)


def inject_text(
    text: str,
    restore_clipboard: bool = True,
    paste_shortcut: str = "auto",
) -> None:
    """Type text at cursor position via clipboard paste."""
    if not text:
        return

    old_clipboard: bytes | None = None
    if restore_clipboard:
        try:
            result = subprocess.run(
                _CLIP_PASTE,
                stdout=subprocess.PIPE,
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
    _simulate_paste(paste_shortcut)
    time.sleep(0.15)  # Increased from 100ms to 150ms

    if restore_clipboard and old_clipboard is not None:
        time.sleep(0.1)
        proc = subprocess.Popen(
            _CLIP_COPY,
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(old_clipboard)


def read_clipboard_text() -> str:
    """Read the current clipboard contents as UTF-8 text when available."""
    try:
        result = subprocess.run(
            _CLIP_PASTE,
            stdout=subprocess.PIPE,
            timeout=1.0,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return ""

    if result.returncode != 0 or not result.stdout:
        return ""

    if isinstance(result.stdout, bytes):
        return result.stdout.decode("utf-8", errors="ignore").strip()
    return str(result.stdout).strip()
