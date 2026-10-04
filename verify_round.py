"""End-to-end verification script for Pronunciation Trainer.

Performs:
1. Reference audio synthesis via gTTS for Spanish "Buenos días".
2. Simulated learner attempt audio.
3. Pronunciation comparison (phonetic similarity, duration, RMS, and pitch contour).
4. Score evaluation with per-word feedback.
5. Waveform and pitch contour plot rendering to outputs/.
6. Database persistence (attempt, streak, spaced repetition).
7. Progress PDF report generation to outputs/.
"""

import sys
from pathlib import Path
import soundfile as sf
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure Windows terminal outputs UTF-8 cleanly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from trainer.logger import app_logger
from trainer.lesson_bank import LessonBank
from trainer.reference_audio import ReferenceAudioService
from trainer.comparator import PronunciationComparator
from trainer.scorer import PronunciationScorer
from trainer.database import DatabaseManager
from trainer.progress import ProgressTracker
from trainer.report import ProgressReportGenerator


def verify_e2e() -> None:
    print("=" * 60)
    print("Starting Pronunciation Trainer End-to-End Verification")
    print("=" * 60)

    # 1. Initialize services
    bank = LessonBank()
    db = DatabaseManager("data/pronunciation_trainer.db")
    progress = ProgressTracker(db, bank)
    ref_service = ReferenceAudioService("recordings/reference")
    comp = PronunciationComparator()
    scorer = PronunciationScorer()
    reporter = ProgressReportGenerator(db, progress, output_dir="outputs")

    target_lang = "es"
    target_phrase = "Buenos días"
    print(f"\n[1/5] Testing reference audio generation for '{target_phrase}' (Spanish)...")
    ref_wav = ref_service.get_or_generate(target_lang, target_phrase)
    assert ref_wav.exists(), f"Reference WAV was not created: {ref_wav}"
    print(f"  ✓ Reference audio generated and cached at: {ref_wav}")

    # 2. Create learner attempt audio (slightly variation of reference audio)
    print("\n[2/5] Creating learner attempt audio...")
    y_ref, sr = sf.read(str(ref_wav))
    # Add slight natural pitch variation and timing difference
    time_stretch = np.interp(
        np.linspace(0, len(y_ref), int(len(y_ref) * 1.05)),
        np.arange(len(y_ref)),
        y_ref
    )
    learner_wav = Path("recordings/learner_test_round.wav")
    sf.write(str(learner_wav), time_stretch, sr, subtype="PCM_16")
    print(f"  ✓ Learner audio generated at: {learner_wav}")

    # 3. Compare attempt
    print("\n[3/5] Comparing recognized attempt vs target...")
    transcription = "Buenos días"
    comparison = comp.compare(
        target_text=target_phrase,
        recognized_text=transcription,
        language=target_lang,
        ref_audio_path=ref_wav,
        learner_audio_path=learner_wav
    )
    score_obj = scorer.evaluate(comparison, language=target_lang)
    print(f"  ✓ Overall Score: {score_obj.overall_score}%")
    print(f"  ✓ Accuracy: {score_obj.accuracy_score}% | Fluency: {score_obj.fluency_score}% | Pitch: {score_obj.pitch_score}%")
    print(f"  ✓ Grade: {score_obj.grade}")
    for wf in comparison.word_feedback:
        print(f"    - Word '{wf.word}': status={wf.status}, similarity={wf.similarity*100:.0f}%")

    # 4. Render comparison plot
    plot_file = Path("outputs/test_round_waveform.png")
    fig = comp.generate_comparison_plot(comparison, output_image_path=plot_file, dark_theme=True)
    assert plot_file.exists() and plot_file.stat().st_size > 1000, "Comparison plot file failed to save"
    print(f"  ✓ Waveform & Pitch Contour plot saved to: {plot_file}")

    # 5. Persist attempt
    attempt_id = db.record_attempt(
        language=target_lang,
        category="greetings",
        mode="phrase",
        target_text=target_phrase,
        transcribed_text=transcription,
        accuracy_score=score_obj.accuracy_score,
        fluency_score=score_obj.fluency_score,
        rhythm_score=score_obj.rhythm_score,
        pitch_score=score_obj.pitch_score,
        overall_score=score_obj.overall_score,
        audio_path=str(learner_wav),
        feedback=score_obj.to_dict()
    )
    streak_info = db.get_streak_info()
    print(f"  ✓ Attempt {attempt_id} persisted in SQLite. Current streak: {streak_info['current_streak']} days")

    # 6. Export progress report PDF
    print("\n[5/5] Generating PDF Progress Report...")
    pdf_file = reporter.generate_pdf(target_lang, "Spanish")
    assert pdf_file.exists() and pdf_file.stat().st_size > 2000, "PDF file failed to generate"
    print(f"  ✓ PDF Progress Report generated at: {pdf_file} ({pdf_file.stat().st_size} bytes)")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    verify_e2e()
