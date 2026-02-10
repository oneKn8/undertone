"""Tests for hotkey management — parse keys, PTT flow, toggle flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from undertone.hotkeys import HotkeyManager, _parse_key


class TestParseKey:
    def test_parse_special_key(self) -> None:
        with patch("undertone.hotkeys.keyboard") as mock_kb:
            mock_kb.Key.ctrl_r = "CTRL_R"
            result = _parse_key("Key.ctrl_r")
            assert result == "CTRL_R"

    def test_parse_function_key(self) -> None:
        with patch("undertone.hotkeys.keyboard") as mock_kb:
            mock_kb.Key.f8 = "F8"
            result = _parse_key("Key.f8")
            assert result == "F8"

    def test_parse_char_key(self) -> None:
        with patch("undertone.hotkeys.keyboard") as mock_kb:
            mock_kb.KeyCode.from_char.return_value = "a"
            result = _parse_key("a")
            assert result == "a"


class TestHotkeyManager:
    def _make_manager(self) -> tuple[HotkeyManager, MagicMock, MagicMock]:
        on_start = MagicMock()
        on_stop = MagicMock()
        with patch("undertone.hotkeys._parse_key", side_effect=lambda x: x):
            manager = HotkeyManager(
                push_to_talk_key="ptt",
                toggle_key="toggle",
                on_start=on_start,
                on_stop=on_stop,
            )
        return manager, on_start, on_stop

    def test_ptt_press_starts_recording(self) -> None:
        manager, on_start, on_stop = self._make_manager()
        manager._on_press("ptt")
        on_start.assert_called_once()
        assert manager._ptt_held is True

    def test_ptt_release_stops_recording(self) -> None:
        manager, on_start, on_stop = self._make_manager()
        manager._on_press("ptt")
        manager._on_release("ptt")
        on_stop.assert_called_once()
        assert manager._ptt_held is False

    def test_ptt_held_no_double_start(self) -> None:
        manager, on_start, on_stop = self._make_manager()
        manager._on_press("ptt")
        manager._on_press("ptt")
        assert on_start.call_count == 1

    def test_toggle_starts_recording(self) -> None:
        manager, on_start, on_stop = self._make_manager()
        manager._on_press("toggle")
        on_start.assert_called_once()
        assert manager._toggle_active is True

    def test_toggle_again_stops_recording(self) -> None:
        manager, on_start, on_stop = self._make_manager()
        manager._on_press("toggle")
        manager._on_press("toggle")
        on_stop.assert_called_once()
        assert manager._toggle_active is False

    def test_ptt_during_toggle_no_stop(self) -> None:
        """PTT release shouldn't stop recording if toggle is active."""
        manager, on_start, on_stop = self._make_manager()
        manager._on_press("toggle")  # Toggle on
        manager._on_press("ptt")  # PTT while toggled
        manager._on_release("ptt")  # Release PTT
        on_stop.assert_not_called()  # Still toggled

    def test_stop_listener(self) -> None:
        manager, _, _ = self._make_manager()
        manager._listener = MagicMock()
        manager.stop()
        manager._listener.stop.assert_called_once()

    def test_stop_no_listener(self) -> None:
        manager, _, _ = self._make_manager()
        manager.stop()  # Should not raise
