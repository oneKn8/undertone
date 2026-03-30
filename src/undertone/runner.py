"""Runner module for systemd service."""

import logging
import sys

from undertone.config import get_api_key, load_config
from undertone.engine import UndertoneEngine


def main():
    """Run the undertone engine."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config()
    api_key = get_api_key()
    primary = str(config.get("stt", {}).get("primary", "groq")).lower()

    if primary == "groq" and not api_key:
        logging.error("No API key configured. Run 'undertone' to set up.")
        sys.exit(1)
    if not api_key:
        logging.warning("No Groq API key configured. Starting in local-only mode.")

    engine = UndertoneEngine(config, api_key=api_key)
    engine.run()


if __name__ == "__main__":
    main()
