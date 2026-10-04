"""Progress tracker, spaced-repetition adaptive scheduler, and mastery analytics."""

import datetime
from typing import List, Dict, Any, Optional
from trainer.lesson_bank import LessonBank, LessonItem
from trainer.database import DatabaseManager
from trainer.logger import app_logger


class ProgressTracker:
    """Manages spaced repetition item selection, category mastery metrics, and learner streaks."""

    def __init__(self, db: DatabaseManager, lesson_bank: LessonBank):
        self.db = db
        self.lesson_bank = lesson_bank

    def get_category_mastery_stats(self, language: str) -> Dict[str, Dict[str, Any]]:
        """
        Calculate mastery metrics for each category in the specified language.

        Returns:
            Dict mapping category_name -> {
                'total_items': int,
                'attempted_items': int,
                'mastered_items': int,
                'mastery_percentage': float,
                'average_score': float
            }
        """
        categories = self.lesson_bank.get_categories()
        mastery_dict = self.db.get_word_mastery_dict(language)
        stats = {}

        for cat in categories:
            cat_items = self.lesson_bank.get_items(language=language, category=cat)
            total = len(cat_items)

            attempted = 0
            mastered = 0
            scores = []

            for item in cat_items:
                m_info = mastery_dict.get(item.target_text)
                if m_info:
                    attempted += 1
                    scores.append(m_info["avg_score"])
                    if m_info["is_mastered"] == 1:
                        mastered += 1

            pct = round((mastered / total * 100.0), 1) if total > 0 else 0.0
            avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

            stats[cat] = {
                "total_items": total,
                "attempted_items": attempted,
                "mastered_items": mastered,
                "mastery_percentage": pct,
                "average_score": avg_score,
            }

        return stats

    def get_adaptive_practice_queue(
        self,
        language: str,
        category: Optional[str] = None,
        item_type: Optional[str] = None,
        limit: int = 20
    ) -> List[LessonItem]:
        """
        Return an adaptively prioritized list of lesson items:
        1. Low-scoring or due review items (highest priority).
        2. Unattempted items (medium priority).
        3. Mastered items (graduated, deprioritized).
        """
        all_candidates = self.lesson_bank.get_items(
            language=language,
            category=category,
            item_type=item_type
        )
        if not all_candidates:
            all_candidates = self.lesson_bank.get_items(language=language)

        mastery_dict = self.db.get_word_mastery_dict(language)
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        urgent_items = []
        unattempted_items = []
        mastered_items = []

        for item in all_candidates:
            m = mastery_dict.get(item.target_text)
            if not m:
                # Unattempted
                unattempted_items.append((item, 100.0))  # Neutral priority
            elif m["is_mastered"] == 1:
                # Graduated: only repeat if review due
                if m.get("next_review_due") and m["next_review_due"] <= today_str:
                    mastered_items.append((item, m["avg_score"]))
                else:
                    # Place at the very end
                    mastered_items.append((item, 999.0))
            else:
                # In progress: lower average score = higher priority
                urgent_items.append((item, m["avg_score"]))

        # Sort urgent by lowest score first
        urgent_items.sort(key=lambda x: x[1])
        # Sort mastered by score
        mastered_items.sort(key=lambda x: x[1])

        # Combine: Urgent items first, then unattempted, then mastered
        combined = [x[0] for x in urgent_items] + [x[0] for x in unattempted_items] + [x[0] for x in mastered_items]
        return combined[:limit]

    def get_learner_dashboard_summary(self, language: str) -> Dict[str, Any]:
        """
        Aggregate high-level stats for the learner overview panel.
        """
        streak_info = self.db.get_streak_info()
        cat_stats = self.get_category_mastery_stats(language)
        recent_attempts = self.db.get_attempts(limit=100, language=language)

        total_mastered = sum(c["mastered_items"] for c in cat_stats.values())
        total_items = sum(c["total_items"] for c in cat_stats.values())
        overall_mastery_pct = round((total_mastered / total_items * 100.0), 1) if total_items > 0 else 0.0

        all_scores = [a["overall_score"] for a in recent_attempts]
        overall_avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

        return {
            "current_streak": streak_info["current_streak"],
            "longest_streak": streak_info["longest_streak"],
            "total_practice_days": streak_info["total_practice_days"],
            "today_practiced": streak_info["today_practiced"],
            "total_attempts": len(recent_attempts),
            "words_mastered": total_mastered,
            "total_words_in_curriculum": total_items,
            "overall_mastery_pct": overall_mastery_pct,
            "overall_avg_score": overall_avg_score,
            "category_breakdown": cat_stats,
        }
