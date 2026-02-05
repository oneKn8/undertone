# speaksy

**talk it. type it. ship it.**

Voice typing for Linux that actually works. Hold a key, speak, release - your words appear wherever you're typing.

## Install

```bash
pipx install speaksy    # recommended
# or
pip3 install speaksy
```

## Setup (30 seconds)

```bash
speaksy
```

That's it. Follow the prompts to add your free Groq API key.

## Usage

| Action | Hotkey |
|--------|--------|
| Push-to-talk | Hold Right Ctrl |
| Toggle mode | Press F8 |

Works everywhere - browser, terminal, IDE, Slack, Discord, anywhere you type.

## Features

- **Fast** - Groq's Whisper API responds in <1 second
- **Smart** - AI cleans up grammar and filler words automatically
- **Free** - Groq's free tier is generous (no credit card needed)
- **Offline fallback** - Works without internet using local Whisper
- **Privacy mode** - Keep your voice 100% local if you prefer
- **Auto-starts** - Runs on login, always ready when you are

## Requirements

- Linux (X11 or XWayland)
- Python 3.10+
- Free Groq API key ([get one here](https://console.groq.com))

## CLI Commands

Run `speaksy` to open the interactive CLI:

| Command | What it does |
|---------|--------------|
| `/setup` | Configure API key, hotkeys, install service |
| `/start` | Start voice typing |
| `/stop` | Stop voice typing |
| `/status` | Show current status |
| `/logs` | View recent activity |
| `/config` | Edit settings |
| `/help` | Show all commands |
| `/quit` | Exit (service keeps running) |

## How it works

1. You press the hotkey (Right Ctrl by default)
2. Speak naturally
3. Release the key
4. Your speech is sent to Groq's Whisper API for transcription
5. An LLM cleans up grammar and removes filler words
6. The text is pasted at your cursor

The whole process takes less than 1 second.

## Privacy

By default, your audio is sent to Groq for transcription. If you prefer to keep everything local:

```
speaksy> /config
# Select "Privacy mode" and choose "local"
```

Local mode uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) running on your CPU. It's slower (~3-5 seconds) but your voice never leaves your machine.

## Troubleshooting

**No audio input detected**
- Check your microphone is connected and working
- Run `arecord -l` to list audio devices

**Text not appearing**
- Make sure xclip and xdotool are installed: `sudo apt install xclip xdotool`
- Some Wayland apps may not work with xdotool

**Service won't start**
- Check logs: `speaksy` then `/logs`
- Verify your API key is valid at console.groq.com

## Uninstall

```bash
speaksy
# Run /stop, then exit

# Remove the package
pipx uninstall speaksy

# Remove config (optional)
rm -rf ~/.config/speaksy
rm ~/.config/systemd/user/speaksy.service
systemctl --user daemon-reload
```

## License

MIT

## Contributing

Issues and PRs welcome at [github.com/oneKn8/speaksy](https://github.com/oneKn8/speaksy)
