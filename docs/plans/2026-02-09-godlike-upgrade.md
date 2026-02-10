# Undertone Godlike Upgrade Plan

## Context

Undertone v0.2.0 is a Linux voice typing tool that works but has a critical UX bug: the LLM cleanup stage sometimes answers questions or follows commands instead of just cleaning up transcribed speech. Beyond that, the codebase is a monolith with no tests, no type hints, no CI/CD, and missing polish like audio feedback, connection pooling, and retry logic.

**User priorities:** Fix the cleanup, make everything feel premium, improve code quality.
**Constraints:** Groq only (no new providers), no voice commands yet, X11 + Wayland.

---

## Phase 1: Fix LLM Cleanup (CRITICAL HOTFIX)

**Problem:** When user dictates "how do I fix this bug", the LLM answers the question instead of cleaning the text. Same for "delete everything" -- treated as a command.

**Root cause:** Transcribed text is sent as a bare user message, so the LLM interprets it as dialogue.

**Files:** `src/undertone/core.py` (lines 216-283)

**Changes:**

1. **Rewrite `CLEANUP_SYSTEM_PROMPT`** with three layers of defense:
   - Role framing: "speech-to-text post-processor" not "text formatter"
   - Identity lock: "You are NOT a chatbot. You do NOT answer questions."
   - Few-shot examples showing questions/commands passed through unchanged

2. **Add boundary markers** -- wrap user input in `<transcript>` tags:
   ```
   {"role": "user", "content": f"<transcript>{text}</transcript>"}
   ```

3. **Add output sanitization** after LLM response:
   - Strip XML tags from response
   - Detect/strip conversational prefixes ("Sure,", "Here is", "I'd be happy to")
   - Tighten length ratio guard from 3.0x to 2.0x
   - Fall back to regex if any sanitization check fires

4. **Lower temperature** from 0.1 to 0.0

**Verify:** Dictate "how do I fix this bug", "delete everything", "what is the meaning of life" -- all should pass through as cleaned text, not answers.

---

## Phase 2: Split `core.py` into Modules

**Problem:** 657-line monolith is untestable and hard to maintain.

**New files under `src/undertone/`:**

| File | Contents | From lines |
|------|----------|-----------|
| `audio.py` | `AudioRecorder` | 38-108 |
| `transcriber.py` | `GroqTranscriber`, `LocalTranscriber`, `route_transcription` | 115-197 |
| `cleanup.py` | `FILLER_PATTERNS`, `CLEANUP_SYSTEM_PROMPT`, `TextCleaner` | 204-303 |
| `injection.py` | `detect_session`, `_detect_tools`, `_simulate_paste`, `inject_text` | 310-394 |
| `tray.py` | `TRAY_COLORS`, `TRAY_TITLES`, `TrayManager`, `HAS_TRAY` | 400-454 |
| `hotkeys.py` | `_parse_key`, `HotkeyManager` | 462-515 |
| `engine.py` | `UndertoneEngine` | 523-657 |

**`core.py` becomes a backward-compat re-export file.**

**Update imports in:** `runner.py`, `setup_wizard.py`

**Verify:** `python -c "from undertone.engine import UndertoneEngine"` + run CLI

---

## Phase 3: Core Experience Improvements

### 3A. Connection Pooling
**Files:** `transcriber.py`, `cleanup.py`, `engine.py`

- Add `httpx.Client()` in `GroqTranscriber.__init__()` and `TextCleaner.__init__()`
- Reuse for all API calls (saves ~50-100ms TLS handshake per request)
- Call `.close()` in `engine.py:shutdown()`

### 3B. Retry Logic with Backoff
**File:** `transcriber.py`

- Retry up to 2 times on 429/500/502/503 and timeouts
- Backoff: 0.3s, then 0.6s
- No retry on 401/400
- Keeps existing fallback-to-local behavior

### 3C. Audio Feedback
**New file:** `sounds.py`

- Pre-generate sine wave beeps using numpy + sounddevice (both already deps)
- "Start" beep: 880Hz, 100ms. "Stop" beep: 440Hz, 150ms descending two-tone
- Play non-blocking in daemon threads
- Works on X11 + Wayland via PulseAudio/PipeWire
- Configurable: `audio.sound_feedback: true` in config

### 3D. Fix `wl-paste` Hanging
**File:** `injection.py`

- Add `--no-newline` to wl-paste
- Reduce clipboard read timeout to 1s
- Suppress stderr on clipboard ops
- Increase post-paste delay from 100ms to 150ms

### 3E. Default Local Model Upgrade
**File:** `config.py`

- Change default from `"base"` to `"distil-large-v3"` (6x faster than large-v3, near-identical accuracy)
- Only affects new installs

---

## Phase 4: Type Hints

**All source files.** Add proper type annotations:

- `config.py`: Add `TypedDict` schemas for config structure
- All modules: Parameter types, return types
- Add `py.typed` marker file (PEP 561)
- Verify: `mypy src/undertone/ --ignore-missing-imports` passes

---

## Phase 5: Comprehensive Tests

**New directory:** `tests/`

| Test file | Coverage |
|-----------|----------|
| `conftest.py` | Shared fixtures (wav buffers, mock configs) |
| `test_cleanup.py` | **Priority 1** -- regex cleanup, LLM cleanup, adversarial inputs |
| `test_transcriber.py` | Groq mock, retry behavior, local mock, routing |
| `test_audio.py` | Mock sounddevice, pre-buffer, WAV output |
| `test_injection.py` | Mock subprocess, session detection, clipboard ops |
| `test_hotkeys.py` | Parse keys, PTT flow, toggle flow |
| `test_config.py` | Deep merge, load/save, defaults |
| `test_engine.py` | Integration test, full pipeline mocked |
| `test_sounds.py` | Beep generation, playback mock |

**Key adversarial tests in `test_cleanup.py`:**
- "how do I fix this bug" must pass through as a cleaned question
- "delete everything" must pass through as cleaned text
- "tell me a joke" must NOT trigger a joke response
- Responses starting with "Sure," or "Here is" must be caught and rejected

**Add dev deps to `pyproject.toml`:** pytest, pytest-cov, pytest-mock, mypy, ruff

**Target:** 80%+ coverage, 90%+ on cleanup.py

---

## Phase 6: CI/CD

**New file:** `.github/workflows/ci.yml`

Three jobs:
1. **lint** -- ruff check + format
2. **type-check** -- mypy
3. **test** -- pytest on Python 3.10, 3.11, 3.12 matrix

**Add tool configs to `pyproject.toml`:** ruff, mypy, pytest sections

---

## Execution Order

```
Phase 1 (LLM fix)  -->  Deploy as v0.2.1 hotfix
       |
Phase 2 (Split)  -->  Enables everything below
       |
  +----+----+----+
  |    |    |    |
 3A   3B   3C  3D/3E  (parallelizable)
       |
Phase 4 (Types)  -->  Can overlap with Phase 3
       |
Phase 5 (Tests)  -->  Depends on Phase 2
       |
Phase 6 (CI/CD)  -->  Depends on Phase 5
```

## Version Plan

| Version | Phases | Description |
|---------|--------|-------------|
| v0.2.1 | 1 | Hotfix: bulletproof LLM cleanup |
| v0.3.0 | 2 + 3 + 4 | Feature: modular architecture, polish, types |
| v0.4.0 | 5 + 6 | Quality: tests, CI/CD |

## Verification

After all phases:
1. Run `pytest tests/ -v --cov=undertone` -- all pass, 80%+ coverage
2. Run `mypy src/undertone/ --ignore-missing-imports` -- no errors
3. Run `ruff check src/undertone/ tests/` -- no issues
4. Manual test: hold key, speak "how do I fix this bug", release -- text appears as cleaned question
5. Manual test: hold key, speak, release -- hear start/stop beeps, text appears in <1s
6. Push to GitHub -- CI passes on all Python versions
