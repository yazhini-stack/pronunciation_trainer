"""Phonetic and acoustic pronunciation comparison engine using Levenshtein, difflib, and librosa."""

import difflib
import math
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False

import librosa
import soundfile as sf
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend safe for threads & GUI embedding
import matplotlib.pyplot as plt

from trainer.logger import app_logger


@dataclass
class WordFeedback:
    """Feedback detail for an individual target word."""
    word: str
    target: str
    recognized: str
    similarity: float  # 0.0 to 1.0
    status: str  # 'correct', 'close', 'mispronounced', 'missing'
    tip: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComparisonResult:
    """Overall comparison and scoring outcome."""
    target_text: str
    recognized_text: str
    accuracy_score: float  # 0 to 100
    fluency_score: float   # 0 to 100
    rhythm_score: float    # 0 to 100
    pitch_score: float     # 0 to 100
    overall_score: float   # 0 to 100
    word_feedback: List[WordFeedback]
    problem_words: List[str]
    feedback_summary: str
    ref_duration: float
    learner_duration: float
    ref_waveform: Optional[np.ndarray] = None
    learner_waveform: Optional[np.ndarray] = None
    ref_f0: Optional[np.ndarray] = None
    learner_f0: Optional[np.ndarray] = None
    sr: int = 22050

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Drop large raw numpy arrays for serialization
        d.pop("ref_waveform", None)
        d.pop("learner_waveform", None)
        d.pop("ref_f0", None)
        d.pop("learner_f0", None)
        return d


def clean_text_for_comparison(text: str) -> str:
    """Clean and normalize text for linguistic comparison."""
    if not text:
        return ""
    # Remove common punctuation while preserving letters and diacritics
    cleaned = re.sub(r"[¿?¡!.,;:\'\"()\[\]{}_-]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def compute_string_similarity(str1: str, str2: str) -> float:
    """Compute normalized similarity ratio between two strings (0.0 to 1.0)."""
    s1, s2 = str1.strip().lower(), str2.strip().lower()
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    if LEVENSHTEIN_AVAILABLE:
        # Use Levenshtein ratio
        return float(Levenshtein.ratio(s1, s2))
    else:
        # Fallback to difflib SequenceMatcher
        return float(difflib.SequenceMatcher(None, s1, s2).ratio())


def align_and_score_words(
    target_text: str,
    recognized_text: str,
    language: str
) -> Tuple[List[WordFeedback], float, List[str]]:
    """
    Perform word-level alignment between target and recognized text.

    Returns:
        (word_feedback_list, text_accuracy_score_0_to_100, problem_words)
    """
    clean_target = clean_text_for_comparison(target_text)
    clean_rec = clean_text_for_comparison(recognized_text)

    target_tokens = clean_target.split()
    rec_tokens = clean_rec.split()

    if not target_tokens:
        return [], 0.0, []

    # If non-Latin script without word spaces (e.g. Japanese or continuous text), also evaluate character chunks
    is_cjk = language.lower() in ["ja", "zh"]
    if is_cjk and len(target_tokens) <= 1 and len(clean_target) > 2:
        target_tokens = list(clean_target)
        rec_tokens = list(clean_rec)

    word_feedbacks: List[WordFeedback] = []
    problem_words: List[str] = []

    # Dynamic programming alignment between target tokens and recognized tokens
    m, n = len(target_tokens), len(rec_tokens)
    dp = np.zeros((m + 1, n + 1), dtype=float)
    trace = np.zeros((m + 1, n + 1), dtype=int)  # 1: match/sub, 2: target skip, 3: rec skip

    for i in range(1, m + 1):
        dp[i][0] = i * -0.5
        trace[i][0] = 2
    for j in range(1, n + 1):
        dp[0][j] = j * -0.5
        trace[0][j] = 3

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            sim = compute_string_similarity(target_tokens[i - 1], rec_tokens[j - 1])
            # Reward high similarity, penalize disparity
            score = (sim - 0.4) * 2.0
            match_val = dp[i - 1][j - 1] + score
            del_val = dp[i - 1][j] - 0.5
            ins_val = dp[i][j - 1] - 0.5

            best = max(match_val, del_val, ins_val)
            dp[i][j] = best
            if best == match_val:
                trace[i][j] = 1
            elif best == del_val:
                trace[i][j] = 2
            else:
                trace[i][j] = 3

    # Backtrack alignment
    i, j = m, n
    aligned_pairs: List[Tuple[Optional[str], Optional[str]]] = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and trace[i][j] == 1:
            aligned_pairs.append((target_tokens[i - 1], rec_tokens[j - 1]))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or trace[i][j] == 2):
            aligned_pairs.append((target_tokens[i - 1], None))
            i -= 1
        else:
            aligned_pairs.append((None, rec_tokens[j - 1]))
            j -= 1

    aligned_pairs.reverse()

    # Evaluate each target word
    scores = []
    for tgt_w, rec_w in aligned_pairs:
        if tgt_w is None:
            # Extra word spoken by learner
            continue

        if rec_w is None:
            sim = 0.0
            status = "missing"
            tip = f"The word '{tgt_w}' was omitted or not heard. Speak it clearly."
            problem_words.append(tgt_w)
        else:
            sim = compute_string_similarity(tgt_w, rec_w)
            if sim >= 0.85:
                status = "correct"
                tip = f"Excellent pronunciation of '{tgt_w}'!"
            elif sim >= 0.60:
                status = "close"
                tip = f"Close! Heard '{rec_w}'. Pay attention to the vowel clarity and vowel length."
                problem_words.append(tgt_w)
            else:
                status = "mispronounced"
                tip = f"Mispronounced: heard '{rec_w}' instead of '{tgt_w}'. Practice this word's syllables slowly."
                problem_words.append(tgt_w)

        scores.append(sim)
        word_feedbacks.append(WordFeedback(
            word=tgt_w,
            target=tgt_w,
            recognized=rec_w if rec_w is not None else "(omitted)",
            similarity=round(sim, 2),
            status=status,
            tip=tip
        ))

    overall_text_acc = float(np.mean(scores) * 100.0) if scores else 0.0
    return word_feedbacks, round(overall_text_acc, 1), problem_words


class PronunciationComparator:
    """Combines speech recognition text comparison with acoustic librosa prosody metrics."""

    def __init__(self, target_sr: int = 22050):
        self.target_sr = target_sr

    def analyze_audio(self, wav_path: Path) -> Tuple[np.ndarray, float, np.ndarray, np.ndarray]:
        """
        Load, trim, and extract F0 pitch contour and RMS energy.

        Returns:
            (y_trimmed, duration_seconds, f0_contour, rms_envelope)
        """
        try:
            y, sr = librosa.load(str(wav_path), sr=self.target_sr, mono=True)
            # Trim leading and trailing silence
            y_trimmed, _ = librosa.effects.trim(y, top_db=25)
            if len(y_trimmed) < 512:
                y_trimmed = y
            duration = float(len(y_trimmed) / sr)

            # RMS Energy
            hop_length = 512
            rms = librosa.feature.rms(y=y_trimmed, frame_length=1024, hop_length=hop_length)[0]

            # Pitch contour via YIN algorithm (efficient and robust for speech)
            f0 = librosa.yin(
                y_trimmed,
                fmin=65,    # approx C2 (low male voice)
                fmax=550,   # approx C#5 (high female/child voice)
                sr=sr,
                frame_length=2048,
                hop_length=hop_length
            )

            # Mask unvoiced or near-silent frames where RMS is very low
            rms_thresh = np.max(rms) * 0.08 if len(rms) > 0 and np.max(rms) > 0 else 0.01
            f0[rms < rms_thresh] = np.nan

            return y_trimmed, duration, f0, rms
        except Exception as e:
            app_logger.warning(f"Audio analysis error for {wav_path}: {e}")
            dummy_y = np.zeros(self.target_sr)
            dummy_f0 = np.full(50, np.nan)
            dummy_rms = np.zeros(50)
            return dummy_y, 1.0, dummy_f0, dummy_rms

    def compare(
        self,
        target_text: str,
        recognized_text: str,
        language: str,
        ref_audio_path: Optional[Path] = None,
        learner_audio_path: Optional[Path] = None
    ) -> ComparisonResult:
        """
        Perform complete multi-modal comparison: textual, phonetic, prosodic, and acoustic.
        """
        app_logger.info(f"Comparing target '{target_text}' vs recognized '{recognized_text}' ({language})")

        # 1. Text & Phonetic similarity
        word_feedbacks, text_accuracy, problem_words = align_and_score_words(
            target_text, recognized_text, language
        )

        ref_dur, rec_dur = 1.0, 1.0
        ref_y, rec_y = None, None
        ref_f0, rec_f0 = None, None
        pitch_score = 75.0
        rhythm_score = 75.0
        fluency_score = 75.0

        # 2. Acoustic comparison if both audio paths provided
        if ref_audio_path and learner_audio_path and ref_audio_path.exists() and learner_audio_path.exists():
            try:
                ref_y, ref_dur, ref_f0, ref_rms = self.analyze_audio(ref_audio_path)
                rec_y, rec_dur, rec_f0, rec_rms = self.analyze_audio(learner_audio_path)

                # Duration ratio score
                if ref_dur > 0 and rec_dur > 0:
                    dur_ratio = min(ref_dur, rec_dur) / max(ref_dur, rec_dur)
                    # Reward speaking close to native cadence
                    duration_score = min(100.0, dur_ratio * 110.0)
                else:
                    duration_score = 70.0

                # Rhythm similarity via normalized RMS correlation
                if len(ref_rms) > 5 and len(rec_rms) > 5:
                    # Resample learner RMS to match ref length for correlation
                    rec_rms_resampled = np.interp(
                        np.linspace(0, 1, len(ref_rms)),
                        np.linspace(0, 1, len(rec_rms)),
                        rec_rms
                    )
                    norm_ref = (ref_rms - np.mean(ref_rms)) / (np.std(ref_rms) + 1e-6)
                    norm_rec = (rec_rms_resampled - np.mean(rec_rms_resampled)) / (np.std(rec_rms_resampled) + 1e-6)
                    rhythm_corr = float(np.clip(np.mean(norm_ref * norm_rec), -1.0, 1.0))
                    rhythm_score = float(np.clip((rhythm_corr + 1.0) / 2.0 * 100.0, 30.0, 100.0))
                else:
                    rhythm_score = duration_score

                # Pitch intonation similarity
                ref_valid_f0 = ref_f0[~np.isnan(ref_f0)]
                rec_valid_f0 = rec_f0[~np.isnan(rec_f0)]

                if len(ref_valid_f0) > 4 and len(rec_valid_f0) > 4:
                    # Pitch contour shape comparison: normalize each pitch contour by its own median
                    # This makes comparison key-invariant (male vs female pitch octave difference won't penalize)
                    ref_norm_pitch = ref_valid_f0 / (np.median(ref_valid_f0) + 1e-6)
                    rec_norm_pitch = rec_valid_f0 / (np.median(rec_valid_f0) + 1e-6)

                    # Resample learner pitch to match reference length
                    rec_pitch_resampled = np.interp(
                        np.linspace(0, 1, len(ref_norm_pitch)),
                        np.linspace(0, 1, len(rec_norm_pitch)),
                        rec_norm_pitch
                    )
                    pitch_diff = np.mean(np.abs(ref_norm_pitch - rec_pitch_resampled))
                    pitch_score = float(np.clip((1.0 - pitch_diff) * 100.0, 20.0, 100.0))
                else:
                    pitch_score = 70.0

                # Fluency score combines rhythm, duration, and pitch stability
                fluency_score = round(0.5 * rhythm_score + 0.3 * duration_score + 0.2 * pitch_score, 1)

            except Exception as e:
                app_logger.error(f"Acoustic comparison failed: {e}")
                fluency_score = 70.0
                pitch_score = 70.0
                rhythm_score = 70.0

        # Overall composite score:
        # 60% text/phonetic accuracy, 25% fluency & rhythm, 15% pitch intonation
        overall_score = round(
            0.60 * text_accuracy + 0.25 * fluency_score + 0.15 * pitch_score, 1
        )

        # Summary message
        if overall_score >= 85:
            summary = "Outstanding pronunciation! Clear diction and natural rhythm."
        elif overall_score >= 70:
            summary = "Good attempt! Understandable with minor phonetic or timing variations."
        elif overall_score >= 50:
            summary = "Fair progress. Focus on the highlighted problem words and repeat."
        else:
            summary = "Needs practice. Listen to the reference audio and try speaking more slowly."

        return ComparisonResult(
            target_text=target_text,
            recognized_text=recognized_text,
            accuracy_score=round(text_accuracy, 1),
            fluency_score=round(fluency_score, 1),
            rhythm_score=round(rhythm_score, 1),
            pitch_score=round(pitch_score, 1),
            overall_score=overall_score,
            word_feedback=word_feedbacks,
            problem_words=problem_words,
            feedback_summary=summary,
            ref_duration=round(ref_dur, 2),
            learner_duration=round(rec_dur, 2),
            ref_waveform=ref_y,
            learner_waveform=rec_y,
            ref_f0=ref_f0,
            learner_f0=rec_f0,
            sr=self.target_sr
        )

    def generate_comparison_plot(
        self,
        result: ComparisonResult,
        output_image_path: Optional[Path] = None,
        dark_theme: bool = True
    ) -> plt.Figure:
        """
        Generate a dual-panel figure with Waveforms and Pitch (F0) Contour overlays.

        Args:
            result: ComparisonResult containing audio arrays and pitch data.
            output_image_path: Optional file path to save as PNG image.
            dark_theme: Whether to render with modern dark theme styling.

        Returns:
            matplotlib.pyplot.Figure object ready for display in Tkinter.
        """
        # Styling parameters
        if dark_theme:
            bg_color = "#1e293b"      # Slate 800
            card_bg = "#0f172a"       # Slate 900
            text_color = "#f8fafc"    # Slate 50
            subtext_color = "#94a3b8" # Slate 400
            grid_color = "#334155"    # Slate 700
            ref_color = "#38bdf8"     # Sky blue
            rec_color = "#34d399"     # Emerald mint
        else:
            bg_color = "#f8fafc"
            card_bg = "#ffffff"
            text_color = "#0f172a"
            subtext_color = "#64748b"
            grid_color = "#e2e8f0"
            ref_color = "#0284c7"
            rec_color = "#059669"

        fig, (ax_wave, ax_pitch) = plt.subplots(2, 1, figsize=(7.2, 4.2), dpi=100)
        fig.patch.set_facecolor(bg_color)

        for ax in (ax_wave, ax_pitch):
            ax.set_facecolor(card_bg)
            ax.tick_params(colors=subtext_color, labelsize=8)
            for spine in ax.spines.values():
                spine.set_color(grid_color)
            ax.grid(True, linestyle="--", alpha=0.4, color=grid_color)

        # 1. Waveforms
        has_ref_wave = result.ref_waveform is not None and len(result.ref_waveform) > 0
        has_rec_wave = result.learner_waveform is not None and len(result.learner_waveform) > 0

        if has_ref_wave:
            ref_times = np.linspace(0, result.ref_duration, len(result.ref_waveform))
            norm_ref_wave = result.ref_waveform / (np.max(np.abs(result.ref_waveform)) + 1e-6)
            ax_wave.plot(ref_times, norm_ref_wave, color=ref_color, alpha=0.75, linewidth=1.2, label=f"Reference ({result.ref_duration:.1f}s)")

        if has_rec_wave:
            rec_times = np.linspace(0, result.learner_duration, len(result.learner_waveform))
            norm_rec_wave = result.learner_waveform / (np.max(np.abs(result.learner_waveform)) + 1e-6)
            ax_wave.plot(rec_times, norm_rec_wave, color=rec_color, alpha=0.8, linewidth=1.2, label=f"Learner ({result.learner_duration:.1f}s)")

        if not has_ref_wave and not has_rec_wave:
            ax_wave.text(0.5, 0.5, "Waveform data not available", color=subtext_color, ha="center", va="center")

        ax_wave.set_title("Waveform Alignment & Timing", color=text_color, fontsize=9, fontweight="bold", pad=4)
        ax_wave.set_ylabel("Amplitude", color=subtext_color, fontsize=8)
        ax_wave.legend(loc="upper right", facecolor=card_bg, edgecolor=grid_color, labelcolor=text_color, fontsize=7)

        # 2. Pitch (F0) Contour Overlay
        has_ref_f0 = result.ref_f0 is not None and len(result.ref_f0) > 0
        has_rec_f0 = result.learner_f0 is not None and len(result.learner_f0) > 0

        if has_ref_f0:
            ref_pitch_times = np.linspace(0, result.ref_duration, len(result.ref_f0))
            ax_pitch.plot(ref_pitch_times, result.ref_f0, color=ref_color, linewidth=2.0, label="Reference F0 (Hz)")

        if has_rec_f0:
            rec_pitch_times = np.linspace(0, result.learner_duration, len(result.learner_f0))
            ax_pitch.plot(rec_pitch_times, result.learner_f0, color=rec_color, linewidth=2.0, linestyle="--", label="Learner F0 (Hz)")

        if not has_ref_f0 and not has_rec_f0:
            ax_pitch.text(0.5, 0.5, "Pitch contour not available", color=subtext_color, ha="center", va="center")

        ax_pitch.set_title("Pitch Contour & Intonation (F0)", color=text_color, fontsize=9, fontweight="bold", pad=4)
        ax_pitch.set_xlabel("Time (seconds)", color=subtext_color, fontsize=8)
        ax_pitch.set_ylabel("Frequency (Hz)", color=subtext_color, fontsize=8)
        ax_pitch.legend(loc="upper right", facecolor=card_bg, edgecolor=grid_color, labelcolor=text_color, fontsize=7)

        plt.tight_layout()

        if output_image_path:
            output_image_path = Path(output_image_path)
            output_image_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(str(output_image_path), dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
            app_logger.info(f"Saved comparison plot to: {output_image_path}")

        return fig
