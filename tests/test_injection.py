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

    @patch("undertone.injection._simulate_paste")
    @patch("undertone.injection.subprocess")
    def test_inject_forwards_paste_shortcut(
        self, mock_subprocess: MagicMock, mock_paste: MagicMock
    ) -> None:
        from undertone.injection import inject_text

        mock_proc = MagicMock()
        mock_subprocess.Popen.return_value = mock_proc
        mock_subprocess.DEVNULL = -1
        mock_run_result = MagicMock()
        mock_run_result.returncode = 1
        mock_subprocess.run.return_value = mock_run_result

        inject_text("Hello world", restore_clipboard=False, paste_shortcut="ctrl_shift_v")

        mock_paste.assert_called_once_with("ctrl_shift_v")


class TestDetectTools:
    @patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=False)
    @patch("undertone.injection.shutil.which")
    def test_x11_uses_xclip(self, mock_which: MagicMock) -> None:
        from undertone.injection import _detect_tools

        mock_which.return_value = "/usr/bin/xclip"
        copy_cmd, _paste_cmd, key_tool = _detect_tools()
        assert copy_cmd == ["xclip", "-sel", "clip"]
        assert key_tool == "xdotool"


class TestPasteShortcutResolution:
    @patch("undertone.injection._get_focused_window_signature", return_value="gnome-terminal vim")
    def test_auto_uses_terminal_shortcut(self, mock_signature: MagicMock) -> None:
        from undertone.injection import _resolve_paste_shortcut

        assert _resolve_paste_shortcut("auto") == "ctrl_shift_v"

    @patch("undertone.injection._get_focused_window_signature", return_value="firefox")
    def test_auto_uses_standard_shortcut_for_normal_apps(self, mock_signature: MagicMock) -> None:
        from undertone.injection import _resolve_paste_shortcut

        assert _resolve_paste_shortcut("auto") == "ctrl_v"


class TestAppContext:
    def test_categorizes_chat_window(self) -> None:
        from undertone.injection import categorize_window_signature

        assert categorize_window_signature("discord general chat") == "chat"

    def test_categorizes_code_editor(self) -> None:
        from undertone.injection import categorize_window_signature

        assert categorize_window_signature("cursor auth.py") == "code_editor"


class TestFocusedWindowSignature:
    @patch("undertone.injection.shutil.which", return_value="/usr/bin/xprop")
    @patch("undertone.injection.subprocess.run")
    def test_uses_xprop_window_class(self, mock_run: MagicMock, mock_which: MagicMock) -> None:
        import undertone.injection as injection

        focus_result = MagicMock(returncode=0, stdout="12345\n")
        name_result = MagicMock(returncode=0, stdout="Project Terminal\n")
        class_result = MagicMock(
            returncode=0,
            stdout='WM_CLASS(STRING) = "gnome-terminal-server", "Gnome-terminal"\n',
        )
        mock_run.side_effect = [focus_result, name_result, class_result]

        with patch.object(injection, "_KEY_TOOL", "xdotool"):
            signature = injection._get_focused_window_signature()

        assert signature == (
            'project terminal wm_class(string) = "gnome-terminal-server", "gnome-terminal"'
        )


class TestSimulatePaste:
    @patch("undertone.injection._resolve_paste_shortcut", return_value="ctrl_shift_v")
    @patch("undertone.injection.subprocess")
    def test_xdotool_terminal_paste(
        self, mock_subprocess: MagicMock, mock_resolve: MagicMock
    ) -> None:
        import undertone.injection as injection

        with patch.object(injection, "_KEY_TOOL", "xdotool"):
            injection._simulate_paste("auto")

        mock_subprocess.run.assert_called_once_with(["xdotool", "key", "ctrl+shift+v"], timeout=2)


class TestReadClipboardText:
    @patch("undertone.injection.subprocess.run")
    def test_reads_clipboard_text(self, mock_run: MagicMock) -> None:
        from undertone.injection import read_clipboard_text

        mock_run.return_value = MagicMock(returncode=0, stdout=b"John\n")

        assert read_clipboard_text() == "John"
