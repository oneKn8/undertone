# Speaksy Design Document

**Date:** 2026-02-05
**Status:** Approved

## Overview

Speaksy is a voice typing tool for Linux. Users speak, and their words appear wherever they're typing.

**Tagline:** talk it. type it. ship it.

## Installation

```bash
pipx install speaksy    # recommended
pip3 install speaksy    # alternative
```

## User Experience

Single command `speaksy` opens an interactive CLI with slash commands:

- `/setup` - Configure API key, hotkeys, install service
- `/start` - Start voice typing service
- `/stop` - Stop voice typing service
- `/status` - Show current status
- `/logs` - View recent activity
- `/config` - Edit settings
- `/help` - Show all commands
- `/quit` - Exit CLI (service keeps running)

### First Run

On first run (no config), auto-triggers `/setup` wizard:

1. Check system deps (xclip, xdotool)
2. Prompt for Groq API key
3. Validate key works
4. Optional: customize hotkeys
5. Install systemd user service
6. Start service

### UI Style

Gen-Z friendly with colors and personality:
- Status messages: "vibing", "sleeping", "dead"
- Helpful with links and next steps
- Error messages are friendly, not scary

## Architecture

### Project Structure

```
speaksy/
├── pyproject.toml
├── README.md
├── LICENSE
└── src/
    └── speaksy/
        ├── __init__.py
        ├── __main__.py
        ├── cli.py
        ├── core.py
        ├── config.py
        ├── service.py
        └── setup_wizard.py
```

### Config Location

- Config: `~/.config/speaksy/config.yaml`
- API key: `~/.config/speaksy/.env`
- Service: `~/.config/systemd/user/speaksy.service`

### Runtime

Always runs as systemd user service. CLI is for management only.

## Features

### Transcription

- **Primary:** Groq Whisper API (fast, <1s)
- **Fallback:** Local faster-whisper (offline, ~3-5s)
- **Cleanup:** LLM post-processing for grammar/filler words

### Hotkeys

- Push-to-talk: Hold Right Ctrl (default)
- Toggle mode: Press F8 (default)
- Customizable via `/config`

### Privacy Mode

Local-only option for users who don't want cloud:
- Uses faster-whisper on CPU
- Voice never leaves the machine
- Slower but private

### Error Handling

- Invalid API key: Warn user, fall back to local
- Expired key: Same behavior
- Network down: Silent fallback to local
- Rate limited: Wait, retry, fallback

### Tray Icon

- Green: Groq API working
- Yellow: Using local fallback
- Red: Both failed

## CLI Commands Detail

### /setup
Interactive wizard for first-time configuration.

### /start
```
speaksy> /start
🚀 lesss gooo! speaksy is now listening...
```

### /stop
```
speaksy> /stop
😴 aight speaksy is taking a nap
```

### /status
```
speaksy> /status
📊 the vibe check:
   ├─ service: running for 2h 34m
   ├─ api key: configured ✓
   └─ mode: cloud (groq)
```

### /config
Interactive menu for:
1. API key
2. Hotkeys
3. Privacy mode (cloud/local)
4. Text cleanup on/off

### /logs
Shows recent transcription activity and errors.

## Dependencies

### Python
- faster-whisper
- sounddevice
- numpy
- pynput
- pystray
- Pillow
- PyYAML
- httpx
- python-dotenv
- rich (for CLI styling)

### System
- xclip
- xdotool
- Python 3.10+

## Success Metrics

- Simple install: 2 commands max
- Setup time: <60 seconds
- First transcription: <30 seconds after setup
