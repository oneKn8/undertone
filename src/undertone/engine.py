"""Main orchestration engine for Undertone."""

from __future__ import annotations

import contextlib
import io
import logging
import os
import signal
import sys
import threading

from undertone.audio import AudioRecorder
from undertone.cleanup import TextCleaner
from undertone.hotkeys import HotkeyManager
from undertone.injection import (
    _CLIP_COPY,
    _KEY_TOOL,
    detect_session,
    get_focused_app_context,
    inject_text,
)
from undertone.learning import save_last_dictation
from undertone.personalization import (
    apply_dictionary_replacements,
    expand_snippet,
    resolve_style,
)
from undertone.sounds import SoundFeedback
from undertone.transcriber import GroqTranscriber, LocalTranscriber, route_transcription
from undertone.tray import HAS_TRAY, TrayManager

log = logging.getLogger("undertone")


class UndertoneEngine:
    """Orchestrates recording, transcription, and text injection."""

    def __init__(self, config: dict, api_key: str = "") -> None:
        self.config = config
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self._recording = False
        self._transcribing = False
        self._using_fallback = False

        # Audio recorder
        audio_cfg = config.get("audio", {})
        self.recorder = AudioRecorder(
            sample_rate=audio_cfg.get("sample_rate", 16000),
            channels=audio_cfg.get("channels", 1),
            pre_buffer_sec=audio_cfg.get("pre_buffer_seconds", 0.5),
        )

        # Sound feedback
        self.sounds = SoundFeedback(
            enabled=audio_cfg.get("sound_feedback", True),
        )

        # Transcribers
        stt_cfg = config.get("stt", {})
        self.groq = GroqTranscriber(
            api_key=self.api_key,
            model=stt_cfg.get("groq_model", "whisper-large-v3-turbo"),
            language=stt_cfg.get("language"),
            prompt=stt_cfg.get("prompt"),
        )
        self.local = LocalTranscriber(
            model_size=stt_cfg.get("local_model", "distil-large-v3"),
            device=stt_cfg.get("local_device", "cpu"),
            compute_type=stt_cfg.get("local_compute_type", "int8"),
        )

        # Text cleaner
        cleanup_cfg = config.get("cleanup", {})
        self.cleaner: TextCleaner | None = None
        if cleanup_cfg.get("enabled", True):
            self.cleaner = TextCleaner(
                api_key=self.api_key,
                model=cleanup_cfg.get("model", "llama-3.1-8b-instant"),
                llm_enabled=cleanup_cfg.get("llm_enabled", True),
            )

        # Tray icon
        tray_cfg = config.get("tray", {})
        self.tray: TrayManager | None = None
        if tray_cfg.get("enabled", True) and HAS_TRAY:
            self.tray = TrayManager(on_quit=self.shutdown)

        # Hotkeys
        hotkey_cfg = config.get("hotkeys", {})
        self.hotkeys = HotkeyManager(
            push_to_talk_key=hotkey_cfg.get("push_to_talk", "Key.ctrl_r"),
            toggle_key=hotkey_cfg.get("toggle", "Key.f8"),
            on_start=self._on_record_start,
            on_stop=self._on_record_stop,
        )

    def _on_record_start(self) -> None:
        if self._recording or self._transcribing:
            return
        self._recording = True
        self.sounds.play_start()
        self.recorder.start_recording()
        if self.tray:
            self.tray.set_state("recording")

    def _on_record_stop(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self.sounds.play_stop()
        audio_buf = self.recorder.stop_recording()
        if audio_buf is None:
            if self.tray:
                self.tray.set_state("ready")
            return

        self._transcribing = True
        if self.tray:
            self.tray.set_state("processing")
        threading.Thread(target=self._transcribe_and_type, args=(audio_buf,), daemon=True).start()

    def _transcribe_and_type(self, audio_buf: io.BytesIO) -> None:
        try:
            text, source = route_transcription(
                audio_buf,
                self.groq,
                self.local,
                self.config,  # type: ignore[arg-type]
            )
            self._using_fallback = source == "local"

            if text:
                raw_text = text
                app_context = get_focused_app_context()
                formatting_cfg = self.config.get("formatting", {})
                resolved_style = resolve_style(
                    str(formatting_cfg.get("style", "auto")),
                    formatting_cfg.get("app_styles"),
                    app_context.get("category", "generic"),
                )

                snippet_cfg = self.config.get("snippets", {})
                dictionary_cfg = self.config.get("dictionary", {})
                snippet_text = None
                if snippet_cfg.get("enabled", True):
                    snippet_text = expand_snippet(text, snippet_cfg.get("items"))

                if snippet_text is not None:
                    log.info(f'[Snippet] "{text}" -> "{snippet_text}"')
                    text = snippet_text
                elif self.cleaner:
                    text = self.cleaner.clean(
                        text,
                        style=resolved_style,
                        app_context=app_context.get("category", "generic"),
                    )

                cleaned_text = text
                text = apply_dictionary_replacements(text, dictionary_cfg.get("replacements"))
                save_last_dictation(
                    raw_text=raw_text,
                    final_text=text,
                    cleaned_text=cleaned_text,
                    app_category=app_context.get("category", "generic"),
                    style=resolved_style,
                )

                text_cfg = self.config.get("text_injection", {})
                inject_text(
                    text,
                    restore_clipboard=text_cfg.get("restore_clipboard", True),
                    paste_shortcut=text_cfg.get("paste_shortcut", "auto"),
                )
        except Exception as e:
            log.error(f"Transcription failed: {e}")
        finally:
            self._transcribing = False
            if self.tray:
                state = "fallback" if self._using_fallback else "ready"
                self.tray.set_state(state)

    def run(self) -> None:
        """Start the engine (blocking)."""
        self.recorder.open()

        # Preload local model in background
        threading.Thread(target=self.local.preload, daemon=True).start()

        self.hotkeys.start()

        session = detect_session()
        log.info(f"Session: {session} | clipboard: {_CLIP_COPY[0]} | keys: {_KEY_TOOL}")

        api_status = "configured" if self.api_key else "NOT SET (local only)"
        log.info(f"Undertone ready. API key: {api_status}")

        hotkey_cfg = self.config.get("hotkeys", {})
        ptt = hotkey_cfg.get("push_to_talk", "Key.ctrl_r")
        toggle = hotkey_cfg.get("toggle", "Key.f8")
        log.info(f"Hold {ptt} (push-to-talk) or press {toggle} (toggle)")

        if self.tray:
            self.tray.start()
        else:
            with contextlib.suppress(KeyboardInterrupt):
                signal.pause()

    def shutdown(self) -> None:
        """Stop the engine and release resources."""
        log.info("Shutting down...")
        self.hotkeys.stop()
        self.recorder.close()
        self.groq.close()
        if self.cleaner:
            self.cleaner.close()
        sys.exit(0)
