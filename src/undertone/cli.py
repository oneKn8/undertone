"""Interactive CLI for Undertone."""

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from undertone import config, service
from undertone.injection import read_clipboard_text
from undertone.learning import learn_from_correction, load_last_dictation
from undertone.setup_wizard import run_setup

console = Console()


def print_banner():
    """Print the undertone banner."""
    banner = """
  [bold cyan]╭────────────────────────────────────────╮[/bold cyan]
  [bold cyan]│[/bold cyan]  [bold white]UNDERTONE[/bold white]                            [bold cyan]│[/bold cyan]
  [bold cyan]│[/bold cyan]  [dim]talk it. type it. ship it.[/dim]           [bold cyan]│[/bold cyan]
  [bold cyan]╰────────────────────────────────────────╯[/bold cyan]
"""
    console.print(banner)


def get_status_display() -> str:
    """Get the current status as a styled string."""
    if not config.is_configured():
        return "[cyan]waiting for setup[/cyan]"
    elif service.is_running():
        return "[green]vibing[/green]"
    else:
        return "[yellow]sleeping[/yellow]"


def print_status_line():
    """Print the current status line."""
    status = get_status_display()
    console.print(f"  [bold]Status:[/bold] {status}")

    if config.is_configured():
        ptt, toggle = config.get_hotkeys()
        ptt_display = ptt.replace("Key.", "").replace("_", " ").title()
        toggle_display = toggle.replace("Key.", "").upper()
        console.print(f"  [bold]Hotkeys:[/bold] {ptt_display} (hold) | {toggle_display} (toggle)")
    console.print()


def print_commands():
    """Print available commands."""
    console.print("  [dim]Commands:[/dim]")
    console.print("    [cyan]/setup[/cyan]   get your keys in here")
    console.print("    [cyan]/start[/cyan]   let's gooo")
    console.print("    [cyan]/stop[/cyan]    take a break")
    console.print("    [cyan]/status[/cyan]  what's the vibe?")
    console.print("    [cyan]/logs[/cyan]    receipts")
    console.print("    [cyan]/config[/cyan]  tweak the drip")
    console.print("    [cyan]/dictionary[/cyan] teach undertone your words")
    console.print("    [cyan]/learn[/cyan]   learn from your last correction")
    console.print("    [cyan]/snippets[/cyan]  voice macros n quick drops")
    console.print("    [cyan]/help[/cyan]    need backup?")
    console.print("    [cyan]/quit[/cyan]    peace out")
    console.print()


def cmd_setup():
    """Run the setup wizard."""
    run_setup()


def cmd_start():
    """Start the service."""
    if not config.is_configured():
        console.print("[yellow]hold up, run /setup first[/yellow]")
        return

    if service.is_running():
        console.print("[yellow]already vibing fam[/yellow]")
        return

    console.print("[dim]starting...[/dim]")
    if service.start_service():
        console.print("[green]lesss gooo! undertone is now listening...[/green]")
        ptt, toggle = config.get_hotkeys()
        ptt_display = ptt.replace("Key.", "").replace("_", " ").title()
        toggle_display = toggle.replace("Key.", "").upper()
        console.print(
            f"   hold [cyan]{ptt_display}[/cyan] or tap [cyan]{toggle_display}[/cyan] to speak"
        )
    else:
        console.print("[red]couldn't start the service[/red]")
        console.print("[dim]check /logs for more info[/dim]")


def cmd_stop():
    """Stop the service."""
    if not service.is_running():
        console.print("[yellow]already sleeping[/yellow]")
        return

    console.print("[dim]stopping...[/dim]")
    if service.stop_service():
        console.print(
            "[yellow]aight undertone is taking a nap. run /start when you need me[/yellow]"
        )
    else:
        console.print("[red]couldn't stop the service[/red]")


def cmd_status():
    """Show detailed status."""
    console.print()
    console.print("[bold]the vibe check:[/bold]")

    status = service.get_status()

    if status["running"]:
        uptime = status.get("uptime", "unknown")
        console.print(f"   [green]|- service: running for {uptime}[/green]")
    elif status["installed"]:
        console.print("   [yellow]|- service: stopped[/yellow]")
    else:
        console.print("   [red]|- service: not installed[/red]")

    if config.api_key_exists():
        console.print("   [green]|- api key: configured[/green]")
    else:
        console.print("   [red]|- api key: not set[/red]")

    mode = config.get_privacy_mode()
    if mode == "local":
        console.print("   [cyan]'- mode: local (privacy mode)[/cyan]")
    else:
        console.print("   [green]'- mode: cloud (groq)[/green]")

    paste_shortcut = config.get_paste_shortcut()
    console.print(f"   [dim]'- paste: {paste_shortcut}[/dim]")
    console.print(f"   [dim]'- style: {config.get_dictation_style()}[/dim]")
    console.print(
        f"   [dim]'- dictionary entries: {len(config.get_dictionary_replacements())}[/dim]"
    )
    console.print(f"   [dim]'- snippets: {len(config.get_snippets())}[/dim]")

    console.print()


def cmd_logs():
    """Show recent logs."""
    console.print()
    console.print("[bold]receipts:[/bold]")
    console.print()
    logs = service.get_logs(lines=15)
    console.print(f"[dim]{logs}[/dim]")
    console.print()


def cmd_config():
    """Interactive config editor."""
    console.print()
    console.print("[bold]settings:[/bold]")
    console.print()
    console.print("  1. API key")
    console.print("  2. Hotkeys")
    console.print("  3. Privacy mode (cloud/local)")
    console.print("  4. Text cleanup on/off")
    console.print("  5. LLM grammar fix on/off")
    console.print("  6. Sound feedback on/off")
    console.print("  7. Language")
    console.print("  8. Whisper prompt (accent/vocab hint)")
    console.print("  9. Paste shortcut (auto/Ctrl+V/Ctrl+Shift+V)")
    console.print("  10. Dictation style (auto/literal/minimal/casual/balanced/polished)")
    console.print("  11. Back")
    console.print()

    choice = Prompt.ask(
        "[cyan]pick one[/cyan]",
        choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
        default="11",
    )

    if choice == "1":
        console.print()
        new_key = Prompt.ask("[cyan]new API key[/cyan]", password=True)
        if new_key:
            config.save_api_key(new_key)
            console.print("[green]saved[/green]")
            if service.is_running():
                service.restart_service()
                console.print("[dim]service restarted[/dim]")

    elif choice == "2":
        console.print()
        console.print("[dim]examples: Key.ctrl_r, Key.f8, Key.alt_l[/dim]")
        ptt, toggle = config.get_hotkeys()

        new_ptt = Prompt.ask("[cyan]push-to-talk[/cyan]", default=ptt)
        new_toggle = Prompt.ask("[cyan]toggle[/cyan]", default=toggle)

        config.set_hotkeys(new_ptt, new_toggle)
        console.print("[green]saved[/green]")

        if service.is_running():
            service.restart_service()
            console.print("[dim]service restarted[/dim]")

    elif choice == "3":
        console.print()
        current = config.get_privacy_mode()
        console.print(f"[dim]currently: {current}[/dim]")
        console.print()
        console.print("  1. [green]cloud[/green] - Groq API, <1s response")
        console.print("  2. [cyan]local[/cyan] - runs on your CPU, ~3-5s response")
        console.print()

        mode_choice = Prompt.ask(
            "[cyan]pick[/cyan]", choices=["1", "2"], default="1" if current == "cloud" else "2"
        )
        new_mode = "cloud" if mode_choice == "1" else "local"
        config.set_privacy_mode(new_mode)

        if new_mode == "local":
            console.print("[cyan]switched to local-only mode[/cyan]")
            console.print("[dim]your voice never leaves your machine[/dim]")
        else:
            console.print("[green]switched to cloud mode[/green]")

        if service.is_running():
            service.restart_service()

    elif choice == "4":
        console.print()
        current = config.get_cleanup_enabled()
        console.print(f"[dim]currently: {'on' if current else 'off'}[/dim]")

        new_state = Confirm.ask("[cyan]enable text cleanup?[/cyan]", default=current)
        config.set_cleanup_enabled(new_state)
        console.print(f"[green]cleanup {'enabled' if new_state else 'disabled'}[/green]")

        if service.is_running():
            service.restart_service()

    elif choice == "5":
        console.print()
        current = config.get_cleanup_llm_enabled()
        console.print(f"[dim]currently: {'on' if current else 'off'}[/dim]")
        console.print("[dim]uses Groq LLM to fix grammar and punctuation[/dim]")

        new_state = Confirm.ask("[cyan]enable LLM grammar fix?[/cyan]", default=current)
        config.set_cleanup_llm_enabled(new_state)
        console.print(f"[green]LLM grammar fix {'enabled' if new_state else 'disabled'}[/green]")

        if service.is_running():
            service.restart_service()

    elif choice == "6":
        console.print()
        current = config.get_sound_feedback()
        console.print(f"[dim]currently: {'on' if current else 'off'}[/dim]")

        new_state = Confirm.ask("[cyan]enable beep sounds?[/cyan]", default=current)
        config.set_sound_feedback(new_state)
        console.print(f"[green]sound feedback {'enabled' if new_state else 'disabled'}[/green]")

        if service.is_running():
            service.restart_service()
            console.print("[dim]service restarted[/dim]")

    elif choice == "7":
        console.print()
        current = config.get_language()
        console.print(f"[dim]currently: {current}[/dim]")
        console.print("[dim]examples: en, es, fr, de, ja, ko, zh, ar, hi, pt[/dim]")
        console.print("[dim]tip: set to your native language for better accuracy[/dim]")
        console.print()

        new_lang = Prompt.ask("[cyan]language code[/cyan]", default=current)
        config.set_language(new_lang)
        console.print(f"[green]language set to '{new_lang}'[/green]")

        if service.is_running():
            service.restart_service()
            console.print("[dim]service restarted[/dim]")

    elif choice == "8":
        console.print()
        current = config.get_whisper_prompt()
        console.print(f"[dim]currently: '{current or '(none)'}' [/dim]")
        console.print("[dim]this hints Whisper about your accent, vocabulary, or topic.[/dim]")
        console.print("[dim]example: 'Technical discussion about Python programming'[/dim]")
        console.print("[dim]example: 'Speaker has an Indian English accent'[/dim]")
        console.print("[dim]leave blank to clear.[/dim]")
        console.print()

        new_prompt = Prompt.ask("[cyan]whisper prompt[/cyan]", default=current)
        config.set_whisper_prompt(new_prompt)
        if new_prompt:
            console.print("[green]whisper prompt set[/green]")
        else:
            console.print("[green]whisper prompt cleared[/green]")

        if service.is_running():
            service.restart_service()
            console.print("[dim]service restarted[/dim]")

    elif choice == "9":
        console.print()
        current = config.get_paste_shortcut()
        console.print(f"[dim]currently: {current}[/dim]")
        console.print(
            "[dim]auto detects common terminal windows on X11 and uses Ctrl+Shift+V[/dim]"
        )
        console.print()
        console.print("  1. [green]auto[/green] - terminal-aware when possible")
        console.print("  2. [cyan]ctrl+v[/cyan] - normal app paste")
        console.print("  3. [cyan]ctrl+shift+v[/cyan] - terminal-friendly paste")
        console.print()

        paste_choice = Prompt.ask("[cyan]pick[/cyan]", choices=["1", "2", "3"], default="1")
        new_shortcut = {
            "1": "auto",
            "2": "ctrl_v",
            "3": "ctrl_shift_v",
        }[paste_choice]
        config.set_paste_shortcut(new_shortcut)
        console.print(f"[green]paste shortcut set to '{new_shortcut}'[/green]")

        if service.is_running():
            service.restart_service()
            console.print("[dim]service restarted[/dim]")

    elif choice == "10":
        console.print()
        current = config.get_dictation_style()
        console.print(f"[dim]currently: {current}[/dim]")
        console.print("[dim]auto uses app-aware defaults like terminal=literal, chat=casual[/dim]")
        console.print()
        console.print("  1. [green]auto[/green]")
        console.print("  2. [cyan]literal[/cyan] - almost verbatim")
        console.print("  3. [cyan]minimal[/cyan] - light cleanup, low polish")
        console.print("  4. [cyan]casual[/cyan] - chat-like cleanup")
        console.print("  5. [cyan]balanced[/cyan] - default readability")
        console.print("  6. [cyan]polished[/cyan] - more professional")
        console.print()

        style_choice = Prompt.ask(
            "[cyan]pick[/cyan]",
            choices=["1", "2", "3", "4", "5", "6"],
            default="1",
        )
        new_style = {
            "1": "auto",
            "2": "literal",
            "3": "minimal",
            "4": "casual",
            "5": "balanced",
            "6": "polished",
        }[style_choice]
        config.set_dictation_style(new_style)
        console.print(f"[green]dictation style set to '{new_style}'[/green]")

        if service.is_running():
            service.restart_service()
            console.print("[dim]service restarted[/dim]")

    console.print()


def cmd_dictionary():
    """Manage dictionary replacements."""
    console.print()
    console.print("[bold]dictionary:[/bold]")
    console.print()

    entries = config.get_dictionary_replacements()
    if entries:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Spoken")
        table.add_column("Written")
        for spoken, written in sorted(entries.items()):
            table.add_row(spoken, written)
        console.print(table)
    else:
        console.print("[dim]no custom dictionary entries yet[/dim]")

    console.print()
    console.print("  1. Add or update entry")
    console.print("  2. Remove entry")
    console.print("  3. Back")
    console.print()

    choice = Prompt.ask("[cyan]pick[/cyan]", choices=["1", "2", "3"], default="3")
    if choice == "1":
        spoken = Prompt.ask("[cyan]spoken phrase[/cyan]").strip()
        written = Prompt.ask("[cyan]written output[/cyan]").strip()
        if spoken and written:
            config.set_dictionary_replacement(spoken, written)
            console.print("[green]dictionary entry saved[/green]")
            if service.is_running():
                service.restart_service()
                console.print("[dim]service restarted[/dim]")
    elif choice == "2":
        if not entries:
            console.print("[yellow]nothing to remove[/yellow]")
        else:
            spoken = Prompt.ask("[cyan]remove spoken phrase[/cyan]").strip()
            if config.remove_dictionary_replacement(spoken):
                console.print("[green]dictionary entry removed[/green]")
                if service.is_running():
                    service.restart_service()
                    console.print("[dim]service restarted[/dim]")
            else:
                console.print("[yellow]couldn't find that dictionary entry[/yellow]")

    console.print()


def cmd_snippets():
    """Manage voice snippets."""
    console.print()
    console.print("[bold]snippets:[/bold]")
    console.print()

    enabled = config.get_snippets_enabled()
    console.print(f"[dim]currently: {'on' if enabled else 'off'}[/dim]")

    items = config.get_snippets()
    if items:
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Trigger")
        table.add_column("Expansion")
        for trigger, expansion in sorted(items.items()):
            table.add_row(trigger, expansion)
        console.print(table)
    else:
        console.print("[dim]no snippets yet[/dim]")

    console.print()
    console.print("  1. Toggle snippets on/off")
    console.print("  2. Add or update snippet")
    console.print("  3. Remove snippet")
    console.print("  4. Back")
    console.print()

    choice = Prompt.ask("[cyan]pick[/cyan]", choices=["1", "2", "3", "4"], default="4")
    if choice == "1":
        config.set_snippets_enabled(not enabled)
        console.print(f"[green]snippets {'enabled' if not enabled else 'disabled'}[/green]")
        if service.is_running():
            service.restart_service()
            console.print("[dim]service restarted[/dim]")
    elif choice == "2":
        trigger = Prompt.ask("[cyan]trigger phrase[/cyan]").strip()
        expansion = Prompt.ask("[cyan]expansion[/cyan]").strip()
        if trigger and expansion:
            config.set_snippet(trigger, expansion)
            console.print("[green]snippet saved[/green]")
            if service.is_running():
                service.restart_service()
                console.print("[dim]service restarted[/dim]")
    elif choice == "3":
        if not items:
            console.print("[yellow]nothing to remove[/yellow]")
        else:
            trigger = Prompt.ask("[cyan]remove trigger phrase[/cyan]").strip()
            if config.remove_snippet(trigger):
                console.print("[green]snippet removed[/green]")
                if service.is_running():
                    service.restart_service()
                    console.print("[dim]service restarted[/dim]")
            else:
                console.print("[yellow]couldn't find that snippet[/yellow]")

    console.print()


def cmd_learn():
    """Learn dictionary replacements from a corrected version of the last dictation."""
    record = load_last_dictation()
    if record is None:
        console.print("[yellow]no recent dictation to learn from yet[/yellow]")
        console.print("[dim]say something first, then fix it, then run /learn[/dim]")
        console.print()
        return

    console.print()
    console.print("[bold]learn from correction:[/bold]")
    console.print(f"[dim]last raw:[/dim] {record.raw_text}")
    console.print(f"[dim]last output:[/dim] {record.final_text}")
    console.print("[dim]tip: copy the corrected text first, or just type it below[/dim]")
    console.print()

    clipboard_text = read_clipboard_text()
    corrected_default = clipboard_text if clipboard_text else record.final_text
    corrected = Prompt.ask("[cyan]corrected text[/cyan]", default=corrected_default).strip()
    if not corrected:
        console.print("[yellow]nothing to learn from[/yellow]")
        console.print()
        return

    learned = learn_from_correction(record.final_text, corrected)
    if not learned:
        console.print("[yellow]i couldn't infer a clean replacement from that edit[/yellow]")
        console.print("[dim]if it was a bigger rewrite, add it manually in /dictionary[/dim]")
        console.print()
        return

    for spoken, written in learned.items():
        config.set_dictionary_replacement(spoken, written)

    console.print("[green]learned new dictionary entries:[/green]")
    for spoken, written in learned.items():
        console.print(f"  [cyan]{spoken}[/cyan] -> [green]{written}[/green]")

    if service.is_running():
        service.restart_service()
        console.print("[dim]service restarted[/dim]")

    console.print()


def cmd_help():
    """Show help."""
    console.print()
    console.print("[bold]undertone commands:[/bold]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    table.add_row("/setup", "Run the setup wizard (API key, hotkeys, etc.)")
    table.add_row("/start", "Start the voice typing service")
    table.add_row("/stop", "Stop the voice typing service")
    table.add_row("/status", "Show detailed status info")
    table.add_row("/logs", "View recent service logs")
    table.add_row("/config", "Edit settings (hotkeys, privacy mode, etc.)")
    table.add_row("/dictionary", "Manage custom replacements like Groq -> Groq")
    table.add_row("/learn", "Infer replacements from your last corrected dictation")
    table.add_row("/snippets", "Manage voice-triggered text expansions")
    table.add_row("/help", "Show this help message")
    table.add_row("/quit", "Exit CLI (service keeps running)")

    console.print(table)
    console.print()
    console.print("[dim]tip: service runs in background, so you can close this anytime[/dim]")
    console.print()


def run_repl():
    """Run the interactive REPL."""
    commands = {
        "/setup": cmd_setup,
        "/start": cmd_start,
        "/stop": cmd_stop,
        "/status": cmd_status,
        "/logs": cmd_logs,
        "/config": cmd_config,
        "/dictionary": cmd_dictionary,
        "/learn": cmd_learn,
        "/snippets": cmd_snippets,
        "/help": cmd_help,
        "/quit": lambda: None,
        "/exit": lambda: None,
        "/q": lambda: None,
    }

    while True:
        try:
            user_input = Prompt.ask("[bold magenta]undertone>[/bold magenta]").strip().lower()

            if not user_input:
                continue

            if user_input in ("/quit", "/exit", "/q"):
                console.print("[dim]peace out[/dim]")
                break

            if user_input in commands:
                commands[user_input]()
            elif user_input.startswith("/"):
                console.print(f"[red]unknown command: {user_input}[/red]")
                console.print("[dim]type /help for available commands[/dim]")
            else:
                console.print("[dim]commands start with / (try /help)[/dim]")

        except KeyboardInterrupt:
            console.print()
            console.print("[dim]peace out[/dim]")
            break
        except EOFError:
            break


def main():
    """Main entry point."""
    print_banner()
    print_status_line()

    # Auto-run setup if not configured
    if not config.is_configured():
        console.print("[yellow]looks like this is your first time![/yellow]")
        console.print("[dim]let's get you set up...[/dim]")
        console.print()
        run_setup()
        console.print()
    else:
        print_commands()

    run_repl()


if __name__ == "__main__":
    main()
