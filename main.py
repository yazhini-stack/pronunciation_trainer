"""Entry point for the pronunciation_trainer application."""

import sys
import tkinter as tk
from pathlib import Path

# Add project root to sys.path if needed
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trainer.logger import app_logger, setup_logger
from trainer.gui import PronunciationTrainerApp


def main() -> None:
    """Launch the pronunciation trainer application."""
    setup_logger()
    app_logger.info("Initializing Pronunciation Trainer application...")

    # Ensure required runtime directories exist
    for dir_name in ["recordings", "outputs", "logs", "data"]:
        (PROJECT_ROOT / dir_name).mkdir(parents=True, exist_ok=True)

    root = tk.Tk()
    app = PronunciationTrainerApp(root)
    app_logger.info("Starting Tkinter main loop.")
    root.mainloop()
    app_logger.info("Pronunciation Trainer shut down cleanly.")


if __name__ == "__main__":
    main()
