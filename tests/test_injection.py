"""Tests for text injection — mock subprocess, session detection, clipboard."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch


class TestDetectSession:
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=False)
    def test_detects_wayland(self) -> None:
        from undertone.injection import detect_session

        assert detect_session() == "wayland"

    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=False)
    def test_detects_x11(self) -> None:
        from undertone.injection import detect_session

        assert detect_session() == "x11"

    @patch.dict(
        os.environ,
        {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "wayland-0"},
        clear=False,
    )
    def test_detects_wayland_from_display(self) -> None:
        from undertone.injection import detect_session

        assert detect_session() == "wayland"

    @patch.dict(
        os.environ,
        {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ":0"},
        clear=False,
    )
    def test_detects_x11_from_display(self) -> None:
        from undertone.injection import detect_session

        assert detect_session() == "x11"

    @patch.dict(
        os.environ,
        {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ""},
        clear=False,
    )
    def test_defaults_to_x11(self) -> None:
        from undertone.injection import detect_session

        assert detect_session() == "x11"


class TestInjectText:
    @patch("undertone.injection._simulate_paste")
    @patch("undertone.injection.subprocess")
    def test_inject_sets_clipboard(
        self, mock_subprocess: MagicMock, mock_paste: MagicMock
    ) -> None:
        from undertone.injection import inject_text

        mock_proc = MagicMock()
        mock_subprocess.Popen.return_value = mock_proc
        mock_subprocess.DEVNULL = -1
        mock_run_result = MagicMock()
        mock_run_result.returncode = 1  # No old clipboard
        mock_subprocess.run.return_value = mock_run_result

        inject_text("Hello world", restore_clipboard=False)

        mock_proc.communicate.assert_called_once_with(b"Hello world")

    @patch("undertone.injection._simulate_paste")
    @patch("undertone.injection.subprocess")
    def test_inject_empty_text(self, mock_subprocess: MagicMock, mock_paste: MagicMock) -> None:
        from undertone.injection import inject_text

        inject_text("", restore_clipboard=False)
        mock_subprocess.Popen.assert_not_called()


class TestDetectTools:
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=False)
    @patch("undertone.injection.shutil.which")
    def test_x11_uses_xclip(self, mock_which: MagicMock) -> None:
        from undertone.injection import _detect_tools

        mock_which.return_value = "/usr/bin/xclip"
        copy_cmd, paste_cmd, key_tool = _detect_tools()
        assert copy_cmd == ["xclip", "-sel", "clip"]
        assert key_tool == "xdotool"
