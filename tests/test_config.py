"""Tests for configuration — deep merge, load/save, defaults."""

from __future__ import annotations

from unittest.mock import MagicMock, mock_open, patch

from undertone.config import (
    DEFAULT_CONFIG,
    api_key_exists,
    deep_merge,
    get_api_key,
    get_hotkeys,
    get_privacy_mode,
    load_config,
)


class TestDeepMerge:
    def test_simple_merge(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99, "z": 100}, "b": 3}

    def test_override_non_dict_with_dict(self) -> None:
        base = {"a": 1}
        override = {"a": {"nested": True}}
        result = deep_merge(base, override)
        assert result == {"a": {"nested": True}}

    def test_override_dict_with_non_dict(self) -> None:
        base = {"a": {"nested": True}}
        override = {"a": 42}
        result = deep_merge(base, override)
        assert result == {"a": 42}

    def test_empty_override(self) -> None:
        base = {"a": 1}
        result = deep_merge(base, {})
        assert result == {"a": 1}

    def test_empty_base(self) -> None:
        result = deep_merge({}, {"a": 1})
        assert result == {"a": 1}

    def test_does_not_mutate_base(self) -> None:
        base = {"a": 1}
        deep_merge(base, {"a": 2})
        assert base == {"a": 1}


class TestDefaultConfig:
    def test_has_stt_section(self) -> None:
        assert "stt" in DEFAULT_CONFIG

    def test_has_cleanup_section(self) -> None:
        assert "cleanup" in DEFAULT_CONFIG

    def test_has_audio_section(self) -> None:
        assert "audio" in DEFAULT_CONFIG

    def test_has_sound_feedback(self) -> None:
        assert DEFAULT_CONFIG["audio"]["sound_feedback"] is True

    def test_default_local_model_is_distil(self) -> None:
        assert DEFAULT_CONFIG["stt"]["local_model"] == "distil-large-v3"

    def test_has_hotkeys_section(self) -> None:
        assert "hotkeys" in DEFAULT_CONFIG

    def test_has_tray_section(self) -> None:
        assert "tray" in DEFAULT_CONFIG


class TestLoadConfig:
    @patch("undertone.config.CONFIG_FILE")
    def test_returns_defaults_when_no_file(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = False
        config = load_config()
        assert config["stt"]["primary"] == "groq"

    @patch("builtins.open", mock_open(read_data="stt:\n  primary: local\n"))
    @patch("undertone.config.CONFIG_FILE")
    def test_merges_user_config(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        config = load_config()
        assert config["stt"]["primary"] == "local"
        # Other defaults should still be present
        assert "cleanup" in config


class TestGetApiKey:
    @patch("undertone.config.ENV_FILE")
    def test_reads_from_env_file(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = True
        with patch("builtins.open", mock_open(read_data="GROQ_API_KEY=gsk_test123\n")):
            key = get_api_key()
        assert key == "gsk_test123"

    @patch("undertone.config.ENV_FILE")
    @patch.dict("os.environ", {"GROQ_API_KEY": "gsk_env_key"})
    def test_falls_back_to_env_var(self, mock_file: MagicMock) -> None:
        mock_file.exists.return_value = False
        key = get_api_key()
        assert key == "gsk_env_key"


class TestApiKeyExists:
    @patch("undertone.config.get_api_key", return_value="gsk_test")
    def test_true_when_key_present(self, mock_get: MagicMock) -> None:
        assert api_key_exists() is True

    @patch("undertone.config.get_api_key", return_value="")
    def test_false_when_key_empty(self, mock_get: MagicMock) -> None:
        assert api_key_exists() is False


class TestHotkeyConfig:
    @patch("undertone.config.load_config")
    def test_get_hotkeys(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {"hotkeys": {"push_to_talk": "Key.alt_l", "toggle": "Key.f9"}}
        ptt, toggle = get_hotkeys()
        assert ptt == "Key.alt_l"
        assert toggle == "Key.f9"


class TestPrivacyMode:
    @patch("undertone.config.load_config")
    def test_cloud_mode(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {"stt": {"primary": "groq"}}
        assert get_privacy_mode() == "cloud"

    @patch("undertone.config.load_config")
    def test_local_mode(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {"stt": {"primary": "local"}}
        assert get_privacy_mode() == "local"
