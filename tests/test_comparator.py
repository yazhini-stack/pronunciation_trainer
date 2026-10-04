"""Comprehensive test suite for comparator, scorer, database, progress, and PDF reporting."""

import os
import sys
import tempfile
from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trainer.comparator import (
    compute_string_similarity,
    clean_text_for_comparison,
    align_and_score_words,
    PronunciationComparator,
    ComparisonResult,
)
from trainer.scorer import PronunciationScorer
from trainer.database import DatabaseManager
from trainer.progress import ProgressTracker
from trainer.lesson_bank import LessonBank
from trainer.report import ProgressReportGenerator


@pytest.fixture
def temp_dirs():
    """Create temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test_trainer.db"
        audio_dir = tmp_path / "audio"
        reports_dir = tmp_path / "reports"
        audio_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)
        yield {
            "root": tmp_path,
            "db_path": db_path,
            "audio_dir": audio_dir,
            "reports_dir": reports_dir,
        }


@pytest.fixture
def synthetic_audio_files(temp_dirs):
    """Generate two synthetic WAV files for acoustic testing."""
    sr = 22050
    t = np.linspace(0, 1.2, int(sr * 1.2))

    # Reference tone: 220 Hz (A3)
    y_ref = 0.5 * np.sin(2 * np.pi * 220 * t)
    ref_path = temp_dirs["audio_dir"] / "ref_test.wav"
    sf.write(str(ref_path), y_ref, sr, subtype="PCM_16")

    # Learner tone: 225 Hz slightly longer
    t_rec = np.linspace(0, 1.3, int(sr * 1.3))
    y_rec = 0.45 * np.sin(2 * np.pi * 225 * t_rec)
    rec_path = temp_dirs["audio_dir"] / "rec_test.wav"
    sf.write(str(rec_path), y_rec, sr, subtype="PCM_16")

    return ref_path, rec_path


class TestPhoneticAndTextComparator:
    """Test string distance, token alignment, and status classification."""

    def test_string_similarity_exact_and_mismatch(self):
        assert compute_string_similarity("hola", "hola") == 1.0
        assert compute_string_similarity("bonjour", "bonjour") == 1.0
        assert compute_string_similarity("hola", "adios") < 0.3
        assert compute_string_similarity("", "test") == 0.0

    def test_text_cleaning(self):
        raw = "¿Cómo estás, amigo?!  "
        cleaned = clean_text_for_comparison(raw)
        assert cleaned == "cómo estás amigo"

    def test_exact_sentence_alignment(self):
        target = "Buenos días"
        recognized = "Buenos días"
        feedbacks, acc, problems = align_and_score_words(target, recognized, "es")

        assert acc >= 99.0
        assert len(feedbacks) == 2
        assert all(wf.status == "correct" for wf in feedbacks)
        assert len(problems) == 0

    def test_partial_match_and_mispronounced(self):
        target = "Buenos días"
        recognized = "Buenos di"  # Partial word
        feedbacks, acc, problems = align_and_score_words(target, recognized, "es")

        assert len(feedbacks) == 2
        assert feedbacks[0].status == "correct"
        assert feedbacks[1].status in ("close", "mispronounced")
        assert "días" in problems

    def test_missing_word(self):
        target = "La cuenta por favor"
        recognized = "La cuenta"
        feedbacks, acc, problems = align_and_score_words(target, recognized, "es")

        assert len(feedbacks) == 4
        assert any(wf.status == "missing" for wf in feedbacks)
        assert "favor" in problems or "por" in problems

    def test_non_latin_script_hindi(self):
        target = "नमस्ते"
        recognized = "नमस्ते"
        feedbacks, acc, _ = align_and_score_words(target, recognized, "hi")
        assert acc == 100.0
        assert feedbacks[0].status == "correct"

    def test_non_latin_script_japanese(self):
        target = "こんにちは"
        recognized = "こんにちは"
        feedbacks, acc, _ = align_and_score_words(target, recognized, "ja")
        assert acc == 100.0


class TestAcousticComparator:
    """Test librosa audio feature extraction and comparison."""

    def test_audio_analysis_synthetic(self, synthetic_audio_files):
        ref_path, _ = synthetic_audio_files
        comp = PronunciationComparator(target_sr=22050)
        y, dur, f0, rms = comp.analyze_audio(ref_path)

        assert len(y) > 0
        assert 1.0 <= dur <= 1.4
        assert len(rms) > 0
        valid_f0 = f0[~np.isnan(f0)]
        assert len(valid_f0) > 0
        # Check median F0 is close to 220 Hz
        assert 180 <= np.median(valid_f0) <= 260

    def test_complete_comparison_and_plot(self, synthetic_audio_files, temp_dirs):
        ref_path, rec_path = synthetic_audio_files
        comp = PronunciationComparator(target_sr=22050)

        result = comp.compare(
            target_text="Hola",
            recognized_text="Hola",
            language="es",
            ref_audio_path=ref_path,
            learner_audio_path=rec_path
        )

        assert result.accuracy_score == 100.0
        assert 0.0 <= result.fluency_score <= 100.0
        assert 0.0 <= result.overall_score <= 100.0
        assert len(result.word_feedback) == 1

        plot_path = temp_dirs["root"] / "test_plot.png"
        fig = comp.generate_comparison_plot(result, output_image_path=plot_path)
        assert fig is not None
        assert plot_path.exists()
        assert plot_path.stat().st_size > 1000


class TestPronunciationScorer:
    """Test grade generation, actionable tips, and mastery thresholds."""

    def test_scorer_mastery_evaluation(self):
        scorer = PronunciationScorer(mastery_cutoff=85.0)

        comp_high = ComparisonResult(
            target_text="Bonjour",
            recognized_text="Bonjour",
            accuracy_score=95.0,
            fluency_score=90.0,
            rhythm_score=88.0,
            pitch_score=85.0,
            overall_score=92.0,
            word_feedback=[],
            problem_words=[],
            feedback_summary="Excellent",
            ref_duration=1.0,
            learner_duration=1.0
        )

        score_high = scorer.evaluate(comp_high, language="fr")
        assert score_high.is_mastery_level is True
        assert "Mastered" in score_high.grade

        comp_low = ComparisonResult(
            target_text="Bonjour",
            recognized_text="Bon",
            accuracy_score=50.0,
            fluency_score=55.0,
            rhythm_score=50.0,
            pitch_score=50.0,
            overall_score=51.0,
            word_feedback=[],
            problem_words=["Bonjour"],
            feedback_summary="Needs Practice",
            ref_duration=1.0,
            learner_duration=1.0
        )

        score_low = scorer.evaluate(comp_low, language="fr")
        assert score_low.is_mastery_level is False
        assert "Developing" in score_low.grade or "Needs Practice" in score_low.grade


class TestDatabaseAndSpacedRepetition:
    """Test SQLite persistence, streak tracking, and adaptive repetition."""

    def test_database_record_and_streak(self, temp_dirs):
        db = DatabaseManager(str(temp_dirs["db_path"]))

        # Record high score attempt
        attempt_id = db.record_attempt(
            language="es",
            category="greetings",
            mode="single_word",
            target_text="Hola",
            transcribed_text="Hola",
            accuracy_score=95.0,
            fluency_score=90.0,
            rhythm_score=90.0,
            pitch_score=90.0,
            overall_score=93.0,
            audio_path="/mock/path.wav",
            feedback={"test": "ok"}
        )

        assert attempt_id > 0
        attempts = db.get_attempts(language="es")
        assert len(attempts) == 1
        assert attempts[0]["target_text"] == "Hola"

        streak = db.get_streak_info()
        assert streak["current_streak"] == 1
        assert streak["today_practiced"] is True

    def test_spaced_repetition_graduation(self, temp_dirs):
        db = DatabaseManager(str(temp_dirs["db_path"]))

        # First high score -> consecutive_mastered = 1 (not yet mastered)
        db.record_attempt(
            language="es", category="greetings", mode="single_word",
            target_text="Gracias", transcribed_text="Gracias",
            accuracy_score=90.0, fluency_score=90.0, rhythm_score=90.0,
            pitch_score=90.0, overall_score=90.0
        )
        m_dict = db.get_word_mastery_dict("es")
        assert m_dict["Gracias"]["consecutive_mastered"] == 1
        assert m_dict["Gracias"]["is_mastered"] == 0

        # Second consecutive high score -> graduates to is_mastered = 1
        db.record_attempt(
            language="es", category="greetings", mode="single_word",
            target_text="Gracias", transcribed_text="Gracias",
            accuracy_score=95.0, fluency_score=95.0, rhythm_score=95.0,
            pitch_score=95.0, overall_score=95.0
        )
        m_dict = db.get_word_mastery_dict("es")
        assert m_dict["Gracias"]["consecutive_mastered"] == 2
        assert m_dict["Gracias"]["is_mastered"] == 1


class TestLessonBankAndProgress:
    """Test lesson bank coverage and adaptive queue scheduling."""

    def test_lesson_bank_coverage(self):
        bank = LessonBank()
        languages = bank.get_languages()
        categories = bank.get_categories()

        assert len(languages) == 6
        for lang_code in languages.keys():
            for cat in categories:
                items = bank.get_items(language=lang_code, category=cat)
                assert len(items) >= 2, f"Missing sufficient items for {lang_code}/{cat}"

    def test_quiz_generator(self):
        bank = LessonBank()
        quiz_items = bank.get_quiz_items(language="es", count=10)
        assert len(quiz_items) == 10

    def test_adaptive_queue_prioritizes_low_scores(self, temp_dirs):
        db = DatabaseManager(str(temp_dirs["db_path"]))
        bank = LessonBank()
        progress = ProgressTracker(db, bank)

        # Give "Hola" a poor score
        db.record_attempt(
            language="es", category="greetings", mode="single_word",
            target_text="Hola", transcribed_text="Ho",
            accuracy_score=40.0, fluency_score=50.0, rhythm_score=40.0,
            pitch_score=40.0, overall_score=42.0
        )

        queue = progress.get_adaptive_practice_queue(language="es", category="greetings")
        # Low scoring item "Hola" must appear at the front of the queue
        assert queue[0].target_text == "Hola"


class TestPDFReportGenerator:
    """Test PDF generation pipeline with analytics charts."""

    def test_pdf_generation_creates_valid_file(self, temp_dirs):
        db = DatabaseManager(str(temp_dirs["db_path"]))
        bank = LessonBank()
        progress = ProgressTracker(db, bank)
        generator = ProgressReportGenerator(db, progress, output_dir=str(temp_dirs["reports_dir"]))

        # Populate a few mock attempts
        db.record_attempt(
            language="es", category="greetings", mode="single_word",
            target_text="Hola", transcribed_text="Hola",
            accuracy_score=95.0, fluency_score=90.0, rhythm_score=85.0,
            pitch_score=88.0, overall_score=92.0
        )
        db.record_attempt(
            language="es", category="numbers", mode="single_word",
            target_text="Uno", transcribed_text="Uno",
            accuracy_score=100.0, fluency_score=95.0, rhythm_score=90.0,
            pitch_score=92.0, overall_score=96.0
        )

        pdf_path = generator.generate_pdf(language="es", language_name="Spanish")
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 2000  # Non-trivial valid PDF
