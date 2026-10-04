"""Scorer module for computing structured pronunciation scores and per-word feedback."""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from trainer.comparator import ComparisonResult, WordFeedback
from trainer.logger import app_logger


@dataclass
class PronunciationScore:
    """Comprehensive score evaluation report for a practice attempt."""
    overall_score: float
    accuracy_score: float
    fluency_score: float
    rhythm_score: float
    pitch_score: float
    grade: str
    grade_color: str
    summary: str
    word_feedbacks: List[Dict[str, Any]]
    words_to_practice: List[str]
    actionable_tips: List[str]
    is_mastery_level: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PronunciationScorer:
    """Evaluates pronunciation attempts and builds structured feedback reports."""

    GRADE_THRESHOLDS = [
        (85.0, "Mastered (A)", "#10b981"),     # Emerald green
        (70.0, "Proficient (B)", "#0ea5e9"),   # Sky blue
        (55.0, "Developing (C)", "#f59e0b"),   # Amber orange
        (0.0, "Needs Practice (D)", "#ef4444") # Crimson red
    ]

    def __init__(self, mastery_cutoff: float = 85.0):
        self.mastery_cutoff = mastery_cutoff

    def get_grade_info(self, score: float) -> tuple[str, str]:
        """Return (grade_label, hex_color) corresponding to overall score."""
        for threshold, label, color in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return label, color
        return "Needs Practice (D)", "#ef4444"

    def evaluate(
        self,
        comparison: ComparisonResult,
        language: str,
        romanization: Optional[str] = None
    ) -> PronunciationScore:
        """
        Produce a final comprehensive PronunciationScore from ComparisonResult.

        Args:
            comparison: Raw comparison output from PronunciationComparator.
            language: Language code.
            romanization: Optional phonetic transliteration for guidance.

        Returns:
            PronunciationScore object.
        """
        grade_label, grade_color = self.get_grade_info(comparison.overall_score)
        is_mastered = comparison.overall_score >= self.mastery_cutoff

        words_to_practice = []
        actionable_tips = []
        word_feedbacks_dict = []

        for wf in comparison.word_feedback:
            word_feedbacks_dict.append(wf.to_dict())
            if wf.status in ("mispronounced", "missing", "close"):
                words_to_practice.append(wf.word)
                actionable_tips.append(f"• {wf.word}: {wf.tip}")

        if not actionable_tips:
            actionable_tips.append("• Superb! All words pronounced with accurate phonetics and natural rhythm.")
        elif len(actionable_tips) > 4:
            actionable_tips = actionable_tips[:4]

        # Additional language-specific general advice
        if comparison.fluency_score < 65.0:
            actionable_tips.append("• Fluency: Try to minimize pauses between syllables and words.")
        if comparison.pitch_score < 60.0:
            actionable_tips.append("• Intonation: Listen to the pitch rise/fall in the reference audio.")

        score_obj = PronunciationScore(
            overall_score=comparison.overall_score,
            accuracy_score=comparison.accuracy_score,
            fluency_score=comparison.fluency_score,
            rhythm_score=comparison.rhythm_score,
            pitch_score=comparison.pitch_score,
            grade=grade_label,
            grade_color=grade_color,
            summary=comparison.feedback_summary,
            word_feedbacks=word_feedbacks_dict,
            words_to_practice=words_to_practice,
            actionable_tips=actionable_tips,
            is_mastery_level=is_mastered
        )

        app_logger.info(
            f"Evaluated pronunciation: Score={score_obj.overall_score}% Grade='{grade_label}' "
            f"Mastered={is_mastered} PracticeWords={len(words_to_practice)}"
        )
        return score_obj
