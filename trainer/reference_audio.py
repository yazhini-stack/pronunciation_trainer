"""Reference audio generation and playback engine using gTTS and pygame/sounddevice."""

import hashlib
import os
import socket
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Tuple
import numpy as np
import soundfile as sf
from gtts import gTTS

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from trainer.logger import app_logger, AudioPlaybackError, NetworkUnavailableError


def check_internet_connection(host: str = "8.8.8.8", port: int = 53, timeout: float = 2.0) -> bool:
    """Check if internet connection is currently accessible."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
        return True
    except (socket.timeout, OSError):
        # Secondary check via HTTP DNS
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(("1.1.1.1", 53))
            return True
        except (socket.timeout, OSError):
            return False


class ReferenceAudioService:
    """Handles generating, caching, and playing reference pronunciation audio."""

    def __init__(self, cache_dir: str = "recordings/reference"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_playing = False
        self._lock = threading.Lock()

        # Initialize audio mixer
        self._init_mixer()

    def _init_mixer(self) -> None:
        """Initialize pygame mixer if available."""
        if PYGAME_AVAILABLE:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                app_logger.info("Pygame audio mixer initialized.")
            except Exception as e:
                app_logger.warning(f"Could not initialize pygame mixer: {e}")

    def _get_cache_keys(self, language: str, text: str) -> Tuple[Path, Path]:
        """Generate deterministic cache file paths for mp3 and wav."""
        clean_key = f"{language.lower().strip()}_{text.strip()}".encode("utf-8")
        hash_digest = hashlib.md5(clean_key).hexdigest()
        mp3_path = self.cache_dir / f"ref_{language.lower()}_{hash_digest}.mp3"
        wav_path = self.cache_dir / f"ref_{language.lower()}_{hash_digest}.wav"
        return mp3_path, wav_path

    def is_cached(self, language: str, text: str) -> bool:
        """Check if reference audio is already cached locally."""
        mp3_path, wav_path = self._get_cache_keys(language, text)
        return wav_path.exists() or mp3_path.exists()

    def get_or_generate(self, language: str, text: str) -> Path:
        """
        Retrieve reference audio from cache or synthesize via gTTS.

        Args:
            language: Language code (e.g., 'es', 'fr', 'hi', 'ta', 'de', 'ja').
            text: Native text string.

        Returns:
            Path to the local WAV reference audio file.

        Raises:
            NetworkUnavailableError: If not cached and no internet connection.
            AudioPlaybackError: If audio synthesis or conversion fails.
        """
        mp3_path, wav_path = self._get_cache_keys(language, text)

        # 1. If WAV already exists, return immediately
        if wav_path.exists() and wav_path.stat().st_size > 0:
            app_logger.debug(f"Cache hit (wav): {wav_path}")
            return wav_path

        # 2. If MP3 exists but not WAV, convert to WAV
        if mp3_path.exists() and mp3_path.stat().st_size > 0:
            try:
                data, samplerate = sf.read(str(mp3_path))
                sf.write(str(wav_path), data, samplerate, subtype="PCM_16")
                return wav_path
            except Exception as e:
                app_logger.warning(f"Failed converting cached MP3 to WAV: {e}")

        # 3. Not cached: check internet connection before requesting gTTS
        if not check_internet_connection():
            app_logger.error(f"Cannot generate reference audio for '{text}' ({language}) while offline.")
            raise NetworkUnavailableError(
                "Reference audio is not cached and requires an active internet connection.\n"
                "Please connect to the internet to download this pronunciation."
            )

        # 4. Fetch via gTTS
        app_logger.info(f"Synthesizing reference audio for '{text}' ({language}) via gTTS...")
        try:
            tts = gTTS(text=text, lang=language, slow=False)
            tts.save(str(mp3_path))

            # Convert to standard 22050Hz or original sample rate WAV for librosa compatibility
            data, samplerate = sf.read(str(mp3_path))
            sf.write(str(wav_path), data, samplerate, subtype="PCM_16")
            app_logger.info(f"Successfully cached reference audio: {wav_path}")
            return wav_path
        except Exception as e:
            app_logger.error(f"gTTS reference audio generation failed: {e}")
            raise AudioPlaybackError(f"Failed to generate reference audio: {e}") from e

    def play(
        self,
        audio_path: Path,
        on_finish: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Play audio file asynchronously in a background thread.

        Args:
            audio_path: Path to the audio file to play.
            on_finish: Optional callback invoked when playback ends.
        """
        self.stop()

        def _play_worker():
            with self._lock:
                self._is_playing = True
                self._stop_event.clear()

            app_logger.info(f"Starting playback: {audio_path}")
            finished_normally = False
            try:
                if PYGAME_AVAILABLE and pygame.mixer.get_init():
                    pygame.mixer.music.load(str(audio_path))
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                        time.sleep(0.05)
                    if self._stop_event.is_set():
                        pygame.mixer.music.stop()
                    else:
                        finished_normally = True
                else:
                    # Fallback using soundfile and sounddevice
                    import sounddevice as sd
                    data, fs = sf.read(str(audio_path), dtype="float32")
                    sd.play(data, fs)
                    total_dur = len(data) / float(fs)
                    start_t = time.time()
                    while (time.time() - start_t < total_dur) and not self._stop_event.is_set():
                        time.sleep(0.05)
                    if self._stop_event.is_set():
                        sd.stop()
                    else:
                        sd.wait()
                        finished_normally = True
            except Exception as e:
                app_logger.error(f"Error during audio playback: {e}")
            finally:
                with self._lock:
                    self._is_playing = False
                if finished_normally and on_finish:
                    try:
                        on_finish()
                    except Exception as cb_err:
                        app_logger.error(f"Error in playback on_finish callback: {cb_err}")

        self._playback_thread = threading.Thread(
            target=_play_worker,
            name="ReferenceAudioPlaybackThread",
            daemon=True
        )
        self._playback_thread.start()

    def stop(self) -> None:
        """Stop any currently active audio playback."""
        self._stop_event.set()
        if PYGAME_AVAILABLE and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        with self._lock:
            self._is_playing = False

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self._is_playing
