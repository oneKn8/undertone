"""Systemd service management for Speaksy."""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from speaksy.config import CONFIG_DIR, ENV_FILE

SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE_FILE = SYSTEMD_USER_DIR / "speaksy.service"

SERVICE_TEMPLATE = """[Unit]
Description=Speaksy - Voice Typing for Linux
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={python_path} -m speaksy.runner
Restart=on-failure
RestartSec=5
EnvironmentFile={env_file}

[Install]
WantedBy=graphical-session.target
"""


def get_python_path() -> str:
    """Get the path to the current Python interpreter."""
    return sys.executable


def install_service() -> bool:
    """Install the systemd user service."""
    try:
        SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)

        service_content = SERVICE_TEMPLATE.format(
            python_path=get_python_path(),
            env_file=ENV_FILE,
        )

        with open(SERVICE_FILE, "w") as f:
            f.write(service_content)

        # Reload systemd
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=True,
            capture_output=True,
        )

        # Enable the service
        subprocess.run(
            ["systemctl", "--user", "enable", "speaksy.service"],
            check=True,
            capture_output=True,
        )

        return True
    except Exception as e:
        return False


def uninstall_service() -> bool:
    """Uninstall the systemd user service."""
    try:
        stop_service()

        subprocess.run(
            ["systemctl", "--user", "disable", "speaksy.service"],
            capture_output=True,
        )

        if SERVICE_FILE.exists():
            SERVICE_FILE.unlink()

        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
        )

        return True
    except Exception:
        return False


def start_service() -> bool:
    """Start the speaksy service."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "start", "speaksy.service"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def stop_service() -> bool:
    """Stop the speaksy service."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "stop", "speaksy.service"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def restart_service() -> bool:
    """Restart the speaksy service."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "restart", "speaksy.service"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_running() -> bool:
    """Check if the speaksy service is running."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "speaksy.service"],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def is_installed() -> bool:
    """Check if the service is installed."""
    return SERVICE_FILE.exists()


def get_uptime() -> str:
    """Get how long the service has been running."""
    try:
        result = subprocess.run(
            [
                "systemctl", "--user", "show", "speaksy.service",
                "--property=ActiveEnterTimestamp",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            line = result.stdout.strip()
            if "=" in line:
                timestamp_str = line.split("=", 1)[1].strip()
                if timestamp_str:
                    # Parse timestamp and calculate uptime
                    try:
                        # Format: "Thu 2026-02-05 16:23:51 CST"
                        from dateutil import parser
                        start_time = parser.parse(timestamp_str)
                        delta = datetime.now(start_time.tzinfo) - start_time
                        hours, remainder = divmod(int(delta.total_seconds()), 3600)
                        minutes, _ = divmod(remainder, 60)
                        if hours > 0:
                            return f"{hours}h {minutes}m"
                        return f"{minutes}m"
                    except Exception:
                        pass
        return "unknown"
    except Exception:
        return "unknown"


def get_logs(lines: int = 20) -> str:
    """Get recent service logs."""
    try:
        result = subprocess.run(
            [
                "journalctl", "--user", "-u", "speaksy.service",
                "-n", str(lines), "--no-pager",
            ],
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else "No logs available"
    except Exception:
        return "Unable to fetch logs"


def get_status() -> dict:
    """Get comprehensive service status."""
    return {
        "installed": is_installed(),
        "running": is_running(),
        "uptime": get_uptime() if is_running() else None,
    }
