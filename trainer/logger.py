"""Logging configuration and custom exceptions for pronunciation_trainer."""

import logging
import os
import sys
from pathlib import Path


class PronunciationTrainerError(Exception):
    """Base exception for all pronunciation trainer errors."""
    pass


class AudioRecordingError(PronunciationTrainerError):
    """Raised when audio recording fails or no microphone is detected."""
    pass


class AudioPlaybackError(PronunciationTrainerError):
    """Raised when audio playback fails."""
    pass


class SpeechRecognitionFailedError(PronunciationTrainerError):
    """Raised when speech recognition fails or cannot understand audio."""
    pass


class NetworkUnavailableError(PronunciationTrainerError):
    """Raised when an operation requires an internet connection that is unavailable."""
    pass


class LessonDataError(PronunciationTrainerError):
    """Raised when lesson bank data is invalid or missing."""
    pass


class DatabaseError(PronunciationTrainerError):
    """Raised when a database query or migration fails."""
    pass


def setup_logger(
    name: str = "pronunciation_trainer",
    log_dir: str = "logs",
    level: int = logging.INFO
) -> logging.Logger:
    """
    Set up and return a thread-safe logger writing to both console and a rotating log file.

    Args:
        name: Name of the logger instance.
        log_dir: Directory where log files are stored.
        level: Logging level (e.g. logging.DEBUG, logging.INFO).

    Returns:
        Configured logging.Logger instance.
    """
    os.makedirs(log_dir, exist_ok=True)
    log_file = Path(log_dir) / "pronunciation_trainer.log"

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] (%(threadName)s) %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # File Handler
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            sys.stderr.write(f"Warning: Could not create log file handler: {e}\n")

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# Default application logger
app_logger = setup_logger()
