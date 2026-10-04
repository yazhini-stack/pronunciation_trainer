"""SQLite persistence layer for pronunciation attempts, word mastery, and daily streaks."""

import datetime
import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from trainer.logger import app_logger, DatabaseError


class DatabaseManager:
    """Thread-safe SQLite database manager for pronunciation trainer."""

    def __init__(self, db_path: str = "data/pronunciation_trainer.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Create required tables and indexes if they do not exist."""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Attempts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        language TEXT NOT NULL,
                        category TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        target_text TEXT NOT NULL,
                        transcribed_text TEXT,
                        accuracy_score REAL NOT NULL,
                        fluency_score REAL NOT NULL,
                        rhythm_score REAL NOT NULL,
                        pitch_score REAL NOT NULL,
                        overall_score REAL NOT NULL,
                        audio_path TEXT,
                        feedback_json TEXT
                    )
                """)

                # Word Mastery table for spaced repetition
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS word_mastery (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        language TEXT NOT NULL,
                        category TEXT NOT NULL,
                        word TEXT NOT NULL,
                        attempts_count INTEGER DEFAULT 0,
                        avg_score REAL DEFAULT 0.0,
                        consecutive_mastered INTEGER DEFAULT 0,
                        last_attempt_date TEXT,
                        is_mastered INTEGER DEFAULT 0,
                        next_review_due TEXT,
                        UNIQUE(language, word)
                    )
                """)

                # Daily streaks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_streaks (
                        date TEXT PRIMARY KEY,
                        attempts_count INTEGER DEFAULT 0,
                        mastered_count INTEGER DEFAULT 0
                    )
                """)

                # Quiz sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        language TEXT NOT NULL,
                        category TEXT NOT NULL,
                        total_items INTEGER NOT NULL,
                        average_score REAL NOT NULL,
                        passed_count INTEGER NOT NULL
                    )
                """)

                # Indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_lang_cat ON attempts(language, category);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_word_mastery_lang ON word_mastery(language, category);")

                conn.commit()
                conn.close()
                app_logger.info(f"Database initialized successfully at: {self.db_path}")
            except Exception as e:
                app_logger.error(f"Failed to initialize database: {e}")
                raise DatabaseError(f"Database initialization failed: {e}") from e

    def record_attempt(
        self,
        language: str,
        category: str,
        mode: str,
        target_text: str,
        transcribed_text: str,
        accuracy_score: float,
        fluency_score: float,
        rhythm_score: float,
        pitch_score: float,
        overall_score: float,
        audio_path: Optional[str] = None,
        feedback: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Record a completed pronunciation attempt and update streaks & mastery.
        """
        now = datetime.datetime.now()
        timestamp_str = now.isoformat()
        today_date_str = now.strftime("%Y-%m-%d")
        feedback_str = json.dumps(feedback or {}, ensure_ascii=False)

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                # 1. Insert attempt
                cursor.execute("""
                    INSERT INTO attempts (
                        timestamp, language, category, mode, target_text,
                        transcribed_text, accuracy_score, fluency_score,
                        rhythm_score, pitch_score, overall_score, audio_path, feedback_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp_str, language, category, mode, target_text,
                    transcribed_text, accuracy_score, fluency_score,
                    rhythm_score, pitch_score, overall_score, audio_path, feedback_str
                ))
                attempt_id = cursor.lastrowid

                # 2. Update daily streak
                cursor.execute("SELECT attempts_count, mastered_count FROM daily_streaks WHERE date = ?", (today_date_str,))
                row = cursor.fetchone()
                is_mastered_hit = 1 if overall_score >= 85.0 else 0
                if row:
                    cursor.execute("""
                        UPDATE daily_streaks
                        SET attempts_count = attempts_count + 1,
                            mastered_count = mastered_count + ?
                        WHERE date = ?
                    """, (is_mastered_hit, today_date_str))
                else:
                    cursor.execute("""
                        INSERT INTO daily_streaks (date, attempts_count, mastered_count)
                        VALUES (?, 1, ?)
                    """, (today_date_str, is_mastered_hit))

                # 3. Update Word Mastery & Spaced Repetition status
                cursor.execute("""
                    SELECT attempts_count, avg_score, consecutive_mastered, is_mastered
                    FROM word_mastery
                    WHERE language = ? AND word = ?
                """, (language, target_text))
                w_row = cursor.fetchone()

                if w_row:
                    old_count = w_row["attempts_count"]
                    old_avg = w_row["avg_score"]
                    old_consec = w_row["consecutive_mastered"]
                    new_count = old_count + 1
                    new_avg = round(((old_avg * old_count) + overall_score) / new_count, 1)

                    if overall_score >= 85.0:
                        new_consec = old_consec + 1
                    else:
                        new_consec = 0

                    # Graduate out of rotation after 2 consecutive scores >= 85%
                    is_mastered = 1 if new_consec >= 2 else 0

                    # Next review interval:
                    # If mastered: 3 days later; if close: 1 day; if low: same day / tomorrow
                    days_ahead = 3 if is_mastered else (1 if overall_score >= 65 else 0)
                    next_review = (now + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

                    cursor.execute("""
                        UPDATE word_mastery
                        SET attempts_count = ?,
                            avg_score = ?,
                            consecutive_mastered = ?,
                            last_attempt_date = ?,
                            is_mastered = ?,
                            next_review_due = ?
                        WHERE language = ? AND word = ?
                    """, (
                        new_count, new_avg, new_consec, timestamp_str,
                        is_mastered, next_review, language, target_text
                    ))
                else:
                    new_consec = 1 if overall_score >= 85.0 else 0
                    is_mastered = 0  # Requires at least 2 consecutive high scores
                    days_ahead = 1 if overall_score >= 65 else 0
                    next_review = (now + datetime.timedelta(days=days_ahead)).strftime("%Y-%m-%d")

                    cursor.execute("""
                        INSERT INTO word_mastery (
                            language, category, word, attempts_count, avg_score,
                            consecutive_mastered, last_attempt_date, is_mastered, next_review_due
                        ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
                    """, (
                        language, category, target_text, overall_score,
                        new_consec, timestamp_str, is_mastered, next_review
                    ))

                conn.commit()
                app_logger.info(f"Recorded attempt {attempt_id} for '{target_text}' (score: {overall_score})")
                return attempt_id
            except Exception as e:
                conn.rollback()
                app_logger.error(f"Failed to record attempt: {e}")
                raise DatabaseError(f"Failed to record attempt: {e}") from e
            finally:
                conn.close()

    def get_streak_info(self) -> Dict[str, Any]:
        """
        Calculate current consecutive daily streak and historical statistics.

        Returns:
            Dict containing current_streak, longest_streak, total_practice_days, today_practiced.
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT date FROM daily_streaks ORDER BY date DESC")
            rows = cursor.fetchall()
            conn.close()

        if not rows:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "total_practice_days": 0,
                "today_practiced": False,
            }

        dates = [datetime.datetime.strptime(r["date"], "%Y-%m-%d").date() for r in rows]
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        today_practiced = dates[0] == today

        # Calculate current streak
        current_streak = 0
        expected_date = today if today_practiced else yesterday

        for d in dates:
            if d == expected_date:
                current_streak += 1
                expected_date -= datetime.timedelta(days=1)
            elif d > expected_date:
                continue
            else:
                break

        # Calculate longest streak
        sorted_dates = sorted(list(set(dates)))
        longest_streak = 0
        run = 0
        for i in range(len(sorted_dates)):
            if i == 0:
                run = 1
            else:
                if sorted_dates[i] == sorted_dates[i - 1] + datetime.timedelta(days=1):
                    run += 1
                else:
                    run = 1
            longest_streak = max(longest_streak, run)

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_practice_days": len(dates),
            "today_practiced": today_practiced,
        }

    def get_word_mastery_dict(self, language: str) -> Dict[str, Dict[str, Any]]:
        """Return dict of {word: mastery_info} for a language."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT word, category, attempts_count, avg_score, consecutive_mastered, is_mastered, next_review_due
                FROM word_mastery
                WHERE language = ?
            """, (language,))
            rows = cursor.fetchall()
            conn.close()

        return {r["word"]: dict(r) for r in rows}

    def get_attempts(
        self,
        limit: int = 50,
        language: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve recent attempts with optional language/category filtering."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = "SELECT * FROM attempts"
            params = []
            conditions = []
            if language:
                conditions.append("language = ?")
                params.append(language)
            if category:
                conditions.append("category = ?")
                params.append(category)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            conn.close()

        results = []
        for r in rows:
            item = dict(r)
            if item.get("feedback_json"):
                try:
                    item["feedback"] = json.loads(item["feedback_json"])
                except Exception:
                    item["feedback"] = {}
            results.append(item)
        return results

    def record_quiz_session(
        self,
        language: str,
        category: str,
        total_items: int,
        average_score: float,
        passed_count: int
    ) -> int:
        """Record a 10-word quiz session summary."""
        timestamp_str = datetime.datetime.now().isoformat()
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO quiz_sessions (timestamp, language, category, total_items, average_score, passed_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp_str, language, category, total_items, average_score, passed_count))
            quiz_id = cursor.lastrowid
            conn.commit()
            conn.close()
        return quiz_id
