"""Learner audio recording service with live metering, silence detection, and speech transcription."""

import datetime
import os
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import numpy as np
import sounddevice as sd
import soundfile as sf
import speech_recognition as sr

from trainer.logger import (
    app_logger,
    AudioRecordingError,
    SpeechRecognitionFailedError,
    NetworkUnavailableError,
)


# Language code mapping for Google Speech Recognition API
SPEECH_RECOGNITION_LANG_MAP: Dict[str, str] = {
    "es": "es-ES",
    "fr": "fr-FR",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "de": "de-DE",
    "ja": "ja-JP",
}


def get_available_microphones() -> List[Dict[str, Any]]:
    """List available input audio devices."""
    devices = []
    try:
        all_devices = sd.query_devices()
        for idx, dev in enumerate(all_devices):
            if dev.get("max_input_channels", 0) > 0:
                devices.append({
                    "id": idx,
                    "name": dev.get("name", f"Microphone {idx}"),
                    "channels": dev.get("max_input_channels"),
                    "sample_rate": dev.get("default_samplerate", 44100),
                })
    except Exception as e:
        app_logger.warning(f"Failed querying audio input devices: {e}")
    return devices


def has_microphone() -> bool:
    """Return True if at least one audio input device is available."""
    return len(get_available_microphones()) > 0


class AudioRecorder:
    """Threaded audio recorder with live VU metering and transcription."""

    def __init__(
        self,
        output_dir: str = "recordings",
        sample_rate: int = 22050,
        channels: int = 1
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = sample_rate
        self.channels = channels

        self._is_recording = False
        self._recorded_frames: List[np.ndarray] = []
        self._record_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._current_audio_file: Optional[Path] = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(
        self,
        level_callback: Optional[Callable[[float], None]] = None
    ) -> None:
        """
        Begin recording audio asynchronously in a background thread.

        Args:
            level_callback: Optional callback receiving normalized RMS amplitude (0.0 to 1.0).

        Raises:
            AudioRecordingError: If microphone is unavailable or recording cannot start.
        """
        if self._is_recording:
            app_logger.warning("Recording is already in progress.")
            return

        if not has_microphone():
            app_logger.error("No microphone detected.")
            raise AudioRecordingError(
                "No microphone detected on your system.\n"
                "Please connect a microphone or check your audio input settings."
            )

        self._stop_event.clear()
        self._recorded_frames = []

        def _record_worker():
            def _audio_callback(indata, frames, time_info, status):
                if status:
                    app_logger.debug(f"Audio stream status: {status}")
                if not self._stop_event.is_set():
                    self._recorded_frames.append(indata.copy())
                    if level_callback:
                        # Calculate RMS for VU meter display
                        rms = float(np.sqrt(np.mean(indata**2)))
                        # Normalize and scale gently for visual responsiveness
                        normalized_level = min(1.0, rms * 8.0)
                        try:
                            level_callback(normalized_level)
                        except Exception:
                            pass

            try:
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="float32",
                    callback=_audio_callback
                ) as stream:
                    self._stream = stream
                    with self._lock:
                        self._is_recording = True
                    app_logger.info("Microphone recording started.")
                    while not self._stop_event.is_set():
                        time.sleep(0.05)
            except Exception as e:
                app_logger.error(f"Failed to start recording stream: {e}")
            finally:
                with self._lock:
                    self._is_recording = False
                    self._stream = None
                if level_callback:
                    try:
                        level_callback(0.0)
                    except Exception:
                        pass
                app_logger.info("Microphone recording stopped.")

        self._record_thread = threading.Thread(
            target=_record_worker,
            name="AudioRecorderThread",
            daemon=True
        )
        self._record_thread.start()

    def stop_recording(self) -> Path:
        """
        Stop the active recording and save data to a 16-bit PCM WAV file.

        Returns:
            Path to the saved WAV file.

        Raises:
            AudioRecordingError: If recording was not active or no audio data was captured.
        """
        if not self._is_recording and not self._recorded_frames:
            raise AudioRecordingError("No recording is currently active or captured.")

        self._stop_event.set()
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=3.0)

        with self._lock:
            self._is_recording = False

        if not self._recorded_frames:
            raise AudioRecordingError("Recording finished but no audio frames were captured.")

        # Concatenate audio frames
        audio_data = np.concatenate(self._recorded_frames, axis=0)

        # Generate unique timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_path = self.output_dir / f"attempt_{timestamp}.wav"

        # Save to disk as 16-bit PCM WAV
        sf.write(str(output_path), audio_data, self.sample_rate, subtype="PCM_16")
        self._current_audio_file = output_path
        app_logger.info(f"Saved recording to: {output_path} (Duration: {len(audio_data)/self.sample_rate:.2f}s)")
        return output_path

    @staticmethod
    def check_silence(audio_path: Path, rms_threshold: float = 0.005) -> bool:
        """
        Check if an audio file contains only silence or near-zero amplitude.

        Args:
            audio_path: Path to the WAV file.
            rms_threshold: Minimum RMS threshold.

        Returns:
            True if the audio is below the threshold (silence), False otherwise.
        """
        try:
            data, _ = sf.read(str(audio_path), dtype="float32")
            if len(data) == 0:
                return True
            rms = float(np.sqrt(np.mean(data**2)))
            return rms < rms_threshold
        except Exception as e:
            app_logger.warning(f"Error checking audio silence: {e}")
            return False

    def transcribe(self, audio_path: Path, language: str) -> str:
        """
        Transcribe the learner's recorded audio using SpeechRecognition.

        Args:
            audio_path: Path to recorded WAV file.
            language: Language code (e.g. 'es', 'fr', 'hi', 'ta', 'de', 'ja').

        Returns:
            Transcribed text.

        Raises:
            SpeechRecognitionFailedError: If audio is unintelligible, silent, or recognition fails.
            NetworkUnavailableError: If speech recognition API cannot be reached.
        """
        if self.check_silence(audio_path):
            raise SpeechRecognitionFailedError("No speech detected. The recording was silent or too quiet.")

        lang_code = SPEECH_RECOGNITION_LANG_MAP.get(language.lower(), "en-US")
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        app_logger.info(f"Transcribing audio file '{audio_path}' with language code '{lang_code}'...")

        try:
            with sr.AudioFile(str(audio_path)) as source:
                # Adjust for ambient noise slightly
                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = recognizer.record(source)

            transcription = recognizer.recognize_google(audio_data, language=lang_code)
            app_logger.info(f"Transcription successful: '{transcription}'")
            return transcription.strip()
        except sr.UnknownValueError:
            app_logger.warning("Google Speech Recognition could not understand audio.")
            raise SpeechRecognitionFailedError(
                "Could not recognize words clearly. Please speak closer to the microphone and try again."
            )
        except sr.RequestError as e:
            app_logger.error(f"Speech recognition service request failed: {e}")
            raise NetworkUnavailableError(
                "Speech recognition service is unreachable. Please verify your internet connection."
            )
        except Exception as e:
            app_logger.error(f"Unexpected speech recognition error: {e}")
            raise SpeechRecognitionFailedError(f"Speech recognition failed: {e}") from e
