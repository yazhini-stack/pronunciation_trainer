"""Modern Tkinter GUI for pronunciation_trainer with real-time audio visualization and feedback."""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

from trainer.logger import (
    app_logger,
    AudioRecordingError,
    AudioPlaybackError,
    SpeechRecognitionFailedError,
    NetworkUnavailableError,
)
from trainer.lesson_bank import LessonBank, LessonItem
from trainer.reference_audio import ReferenceAudioService
from trainer.recorder import AudioRecorder, has_microphone
from trainer.comparator import PronunciationComparator, ComparisonResult
from trainer.scorer import PronunciationScorer, PronunciationScore
from trainer.database import DatabaseManager
from trainer.progress import ProgressTracker
from trainer.report import ProgressReportGenerator


class PronunciationTrainerApp:
    """Main Application GUI controller."""

    # Color Palette - Modern Dark Slate
    BG_COLOR = "#0f172a"        # Slate 900
    PANEL_BG = "#1e293b"        # Slate 800
    CARD_BG = "#1e293b"         # Slate 800
    BORDER_COLOR = "#334155"    # Slate 700
    ACCENT_CYAN = "#0ea5e9"     # Sky 500
    ACCENT_GREEN = "#10b981"    # Emerald 500
    ACCENT_AMBER = "#f59e0b"    # Amber 500
    ACCENT_RED = "#ef4444"      # Red 500
    TEXT_LIGHT = "#f8fafc"      # Slate 50
    TEXT_MUTED = "#94a3b8"      # Slate 400

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Pronunciation Trainer — Speech & Prosody Coach")
        self.root.geometry("1240x840")
        self.root.minsize(1050, 720)
        self.root.configure(bg=self.BG_COLOR)

        # Services
        self.lesson_bank = LessonBank()
        self.db = DatabaseManager()
        self.progress_tracker = ProgressTracker(self.db, self.lesson_bank)
        self.ref_audio_service = ReferenceAudioService()
        self.recorder = AudioRecorder()
        self.comparator = PronunciationComparator()
        self.scorer = PronunciationScorer()
        self.report_generator = ProgressReportGenerator(self.db, self.progress_tracker)

        # State Variables
        self.current_language_code = "es"
        self.current_category = "greetings"
        self.current_mode = "single_word"  # single_word, phrase, timed_quiz
        self.current_queue: List[LessonItem] = []
        self.current_index = 0
        self.current_ref_audio_path: Optional[Path] = None
        self.current_learner_audio_path: Optional[Path] = None
        self.current_comparison: Optional[ComparisonResult] = None
        self.current_score: Optional[PronunciationScore] = None

        # Quiz State
        self.is_quiz_active = False
        self.quiz_items: List[LessonItem] = []
        self.quiz_index = 0
        self.quiz_scores: List[float] = []

        # Recording Timer & VU meter state
        self._record_start_time: float = 0.0
        self._vu_meter_val = tk.DoubleVar(value=0.0)

        # Setup custom dark ttk styling
        self._setup_styles()

        # Build UI layout
        self._build_header()
        self._build_main_content()
        self._build_status_bar()

        # Load initial lesson items
        self._reload_lesson_queue()
        self._display_current_item()

        # Handle window close cleanly
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self) -> None:
        """Configure ttk styles for dark modern aesthetic."""
        style = ttk.Style()
        style.theme_use("clam")

        # Base Frame & Label styling
        style.configure("TFrame", background=self.BG_COLOR)
        style.configure("Panel.TFrame", background=self.PANEL_BG)
        style.configure("Card.TFrame", background=self.CARD_BG, relief="flat")

        style.configure("TLabel", background=self.BG_COLOR, foreground=self.TEXT_LIGHT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=self.PANEL_BG, foreground=self.TEXT_LIGHT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.PANEL_BG, foreground=self.TEXT_MUTED, font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=self.BG_COLOR, foreground=self.TEXT_LIGHT, font=("Segoe UI", 14, "bold"))
        style.configure("TargetText.TLabel", background=self.CARD_BG, foreground="#38bdf8", font=("Segoe UI", 26, "bold"))
        style.configure("Roman.TLabel", background=self.CARD_BG, foreground=self.TEXT_LIGHT, font=("Segoe UI", 13, "italic"))
        style.configure("Trans.TLabel", background=self.CARD_BG, foreground=self.TEXT_MUTED, font=("Segoe UI", 11))

        # Buttons
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=self.ACCENT_CYAN, foreground="#ffffff", borderwidth=0, padding=6)
        style.map("Primary.TButton", background=[("active", "#0284c7")])

        style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background=self.ACCENT_GREEN, foreground="#ffffff", borderwidth=0, padding=6)
        style.map("Success.TButton", background=[("active", "#059669")])

        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), background=self.ACCENT_RED, foreground="#ffffff", borderwidth=0, padding=6)
        style.map("Danger.TButton", background=[("active", "#dc2626")])

        style.configure("Secondary.TButton", font=("Segoe UI", 9), background="#334155", foreground="#ffffff", borderwidth=0, padding=5)
        style.map("Secondary.TButton", background=[("active", "#475569")])

        # Progressbar for VU meter
        style.configure("VU.Horizontal.TProgressbar", background=self.ACCENT_GREEN, troughcolor="#334155", borderwidth=0)

        # Combobox
        style.configure("TCombobox", fieldbackground="#1e293b", background="#334155", foreground=self.TEXT_LIGHT, font=("Segoe UI", 10))

    def _build_header(self) -> None:
        """Top navigation bar with language, category, mode selectors and stats."""
        header_frame = tk.Frame(self.root, bg=self.PANEL_BG, padx=16, pady=10, relief="flat", highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        header_frame.pack(fill="x", side="top")

        # Title Brand
        title_box = tk.Frame(header_frame, bg=self.PANEL_BG)
        title_box.pack(side="left")
        logo_lbl = tk.Label(title_box, text="🗣️ Pronunciation Trainer", font=("Segoe UI", 15, "bold"), fg=self.TEXT_LIGHT, bg=self.PANEL_BG)
        logo_lbl.pack(side="left", padx=(0, 20))

        # Controls Selector Row
        ctrl_box = tk.Frame(header_frame, bg=self.PANEL_BG)
        ctrl_box.pack(side="left", fill="x", expand=True)

        # Language Selector
        tk.Label(ctrl_box, text="Language:", font=("Segoe UI", 9, "bold"), fg=self.TEXT_MUTED, bg=self.PANEL_BG).pack(side="left", padx=(5, 4))
        self.lang_var = tk.StringVar(value="Spanish")
        languages = self.lesson_bank.get_languages()
        self.lang_names = list(languages.values())
        self.lang_codes = {v: k for k, v in languages.items()}
        self.lang_combo = ttk.Combobox(ctrl_box, textvariable=self.lang_var, values=self.lang_names, state="readonly", width=11)
        self.lang_combo.pack(side="left", padx=(0, 15))
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)

        # Category Selector
        tk.Label(ctrl_box, text="Category:", font=("Segoe UI", 9, "bold"), fg=self.TEXT_MUTED, bg=self.PANEL_BG).pack(side="left", padx=(5, 4))
        self.cat_var = tk.StringVar(value="Greetings")
        self.cat_names = [c.capitalize() for c in self.lesson_bank.get_categories()]
        self.cat_combo = ttk.Combobox(ctrl_box, textvariable=self.cat_var, values=self.cat_names, state="readonly", width=12)
        self.cat_combo.pack(side="left", padx=(0, 15))
        self.cat_combo.bind("<<ComboboxSelected>>", self._on_category_change)

        # Practice Mode Selector
        tk.Label(ctrl_box, text="Mode:", font=("Segoe UI", 9, "bold"), fg=self.TEXT_MUTED, bg=self.PANEL_BG).pack(side="left", padx=(5, 4))
        self.mode_var = tk.StringVar(value="Single Word")
        self.mode_map = {
            "Single Word": "single_word",
            "Phrase": "phrase",
            "Timed Quiz (10 Words)": "timed_quiz",
        }
        self.mode_combo = ttk.Combobox(ctrl_box, textvariable=self.mode_var, values=list(self.mode_map.keys()), state="readonly", width=18)
        self.mode_combo.pack(side="left", padx=(0, 15))
        self.mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)

        # Streak Badge
        self.streak_badge = tk.Label(
            header_frame,
            text="🔥 Streak: 0 Days",
            font=("Segoe UI", 10, "bold"),
            fg="#f59e0b",
            bg="#292524",
            padx=10,
            pady=4,
            relief="groove",
            bd=1
        )
        self.streak_badge.pack(side="left", padx=(10, 12))
        self._update_streak_badge()

        # Mastery Dashboard Button
        btn_mastery = ttk.Button(header_frame, text="📊 Mastery Dashboard", style="Secondary.TButton", command=self._show_mastery_modal)
        btn_mastery.pack(side="left", padx=(0, 8))

        # PDF Export Button
        btn_pdf = ttk.Button(header_frame, text="📄 Export PDF Report", style="Secondary.TButton", command=self._export_pdf_report)
        btn_pdf.pack(side="left", padx=(0, 5))

    def _build_main_content(self) -> None:
        """2-column main practice station and analytics feedback area."""
        content_frame = tk.Frame(self.root, bg=self.BG_COLOR, padx=12, pady=10)
        content_frame.pack(fill="both", expand=True)

        # ---------------- LEFT COLUMN: Lesson Card & Controls ----------------
        left_col = tk.Frame(content_frame, bg=self.PANEL_BG, padx=14, pady=12, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Top tag row: Item Type pill & Spaced Repetition Pill
        tag_row = tk.Frame(left_col, bg=self.PANEL_BG)
        tag_row.pack(fill="x", pady=(0, 10))

        self.mode_pill = tk.Label(tag_row, text="SINGLE WORD", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0c4a6e", padx=8, pady=2)
        self.mode_pill.pack(side="left", padx=(0, 8))

        self.mastery_pill = tk.Label(tag_row, text="UNSEEN", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#334155", padx=8, pady=2)
        self.mastery_pill.pack(side="left")

        self.item_counter_lbl = tk.Label(tag_row, text="Item 1 of 10", font=("Segoe UI", 9), fg=self.TEXT_MUTED, bg=self.PANEL_BG)
        self.item_counter_lbl.pack(side="right")

        # Large Target Text Card
        target_card = tk.Frame(left_col, bg="#0f172a", padx=16, pady=20, highlightthickness=1, highlightbackground="#334155")
        target_card.pack(fill="x", pady=(0, 10))

        self.target_text_lbl = tk.Label(target_card, text="Hola", font=("Segoe UI", 30, "bold"), fg="#38bdf8", bg="#0f172a", wraplength=480)
        self.target_text_lbl.pack(pady=(0, 4))

        self.roman_lbl = tk.Label(target_card, text="[OH-lah]", font=("Segoe UI", 13, "italic"), fg="#f8fafc", bg="#0f172a", wraplength=480)
        self.roman_lbl.pack(pady=(0, 4))

        self.trans_lbl = tk.Label(target_card, text="Hello", font=("Segoe UI", 12), fg="#94a3b8", bg="#0f172a")
        self.trans_lbl.pack(pady=(0, 4))

        # Phonetic Tips Box
        tips_card = tk.Frame(left_col, bg="#1e293b", padx=10, pady=8, highlightthickness=1, highlightbackground="#334155")
        tips_card.pack(fill="x", pady=(0, 10))
        tk.Label(tips_card, text="💡 Pronunciation Guidance:", font=("Segoe UI", 9, "bold"), fg="#f59e0b", bg="#1e293b").pack(anchor="w")
        self.tip_lbl = tk.Label(tips_card, text="The 'H' is completely silent in Spanish.", font=("Segoe UI", 9), fg=self.TEXT_LIGHT, bg="#1e293b", wraplength=480, justify="left")
        self.tip_lbl.pack(anchor="w", pady=(2, 0))

        # Interactive Audio Buttons
        audio_btn_frame = tk.Frame(left_col, bg=self.PANEL_BG)
        audio_btn_frame.pack(fill="x", pady=(5, 8))

        self.btn_listen = ttk.Button(audio_btn_frame, text="🔊 Listen Reference", style="Primary.TButton", command=self._play_reference_audio)
        self.btn_listen.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_record = ttk.Button(audio_btn_frame, text="🎤 Record My Attempt", style="Success.TButton", command=self._toggle_recording)
        self.btn_record.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # Live VU Meter & Recording Status
        meter_frame = tk.Frame(left_col, bg=self.PANEL_BG)
        meter_frame.pack(fill="x", pady=(2, 8))
        self.rec_status_lbl = tk.Label(meter_frame, text="Ready to record", font=("Segoe UI", 9), fg=self.TEXT_MUTED, bg=self.PANEL_BG)
        self.rec_status_lbl.pack(side="left")

        self.vu_meter = ttk.Progressbar(meter_frame, style="VU.Horizontal.TProgressbar", variable=self._vu_meter_val, maximum=100, length=180)
        self.vu_meter.pack(side="right")

        # Feedback & Notification Banner
        self.banner_frame = tk.Frame(left_col, bg="#334155", padx=10, pady=8)
        self.banner_frame.pack(fill="x", pady=(4, 10))
        self.banner_lbl = tk.Label(self.banner_frame, text="Click 'Listen Reference' to hear pronunciation, then record your attempt.", font=("Segoe UI", 9), fg=self.TEXT_LIGHT, bg="#334155", wraplength=480, justify="left")
        self.banner_lbl.pack(anchor="w")

        # Actionable Syllable & Sound Tips Box
        action_card = tk.Frame(left_col, bg="#0f172a", padx=10, pady=8, highlightthickness=1, highlightbackground="#334155")
        action_card.pack(fill="x", pady=(0, 10))
        tk.Label(action_card, text="🎯 Personalized Coach Tips:", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#0f172a").pack(anchor="w")
        self.action_tips_lbl = tk.Label(action_card, text="Record an attempt to see targeted feedback on specific sounds.", font=("Segoe UI", 9), fg=self.TEXT_MUTED, bg="#0f172a", wraplength=480, justify="left")
        self.action_tips_lbl.pack(anchor="w", pady=(2, 0))

        # Bottom Navigation Controls
        nav_row = tk.Frame(left_col, bg=self.PANEL_BG)
        nav_row.pack(fill="x", side="bottom", pady=(6, 0))

        btn_prev = ttk.Button(nav_row, text="◀ Previous", style="Secondary.TButton", command=self._prev_item)
        btn_prev.pack(side="left", padx=(0, 6))

        btn_shuffle = ttk.Button(nav_row, text="🔀 Shuffle", style="Secondary.TButton", command=self._shuffle_queue)
        btn_shuffle.pack(side="left", padx=(0, 6))

        self.btn_next = ttk.Button(nav_row, text="Next Item ▶", style="Primary.TButton", command=self._next_item)
        self.btn_next.pack(side="right")

        # ---------------- RIGHT COLUMN: Score Cards & Waveform/Pitch ----------------
        right_col = tk.Frame(content_frame, bg=self.PANEL_BG, padx=12, pady=12, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
        right_col.pack(side="right", fill="both", expand=True, padx=(8, 0))

        # Score Cards Header Row
        score_row = tk.Frame(right_col, bg=self.PANEL_BG)
        score_row.pack(fill="x", pady=(0, 8))

        # Overall Score Card
        self.overall_card = tk.Frame(score_row, bg="#0f172a", padx=12, pady=8, highlightthickness=1, highlightbackground="#334155")
        self.overall_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(self.overall_card, text="OVERALL SCORE", font=("Segoe UI", 8, "bold"), fg=self.TEXT_MUTED, bg="#0f172a").pack()
        self.overall_score_lbl = tk.Label(self.overall_card, text="-- %", font=("Segoe UI", 20, "bold"), fg="#10b981", bg="#0f172a")
        self.overall_score_lbl.pack()
        self.grade_pill = tk.Label(self.overall_card, text="Pending", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#1e293b", padx=6, pady=1)
        self.grade_pill.pack(pady=(2, 0))

        # Accuracy Score Card
        self.acc_card = tk.Frame(score_row, bg="#0f172a", padx=12, pady=8, highlightthickness=1, highlightbackground="#334155")
        self.acc_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(self.acc_card, text="PHONETICS", font=("Segoe UI", 8, "bold"), fg=self.TEXT_MUTED, bg="#0f172a").pack()
        self.acc_score_lbl = tk.Label(self.acc_card, text="-- %", font=("Segoe UI", 18, "bold"), fg="#38bdf8", bg="#0f172a")
        self.acc_score_lbl.pack()
        tk.Label(self.acc_card, text="Word Accuracy", font=("Segoe UI", 8), fg=self.TEXT_MUTED, bg="#0f172a").pack()

        # Fluency Score Card
        self.flu_card = tk.Frame(score_row, bg="#0f172a", padx=12, pady=8, highlightthickness=1, highlightbackground="#334155")
        self.flu_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(self.flu_card, text="FLUENCY", font=("Segoe UI", 8, "bold"), fg=self.TEXT_MUTED, bg="#0f172a").pack()
        self.flu_score_lbl = tk.Label(self.flu_card, text="-- %", font=("Segoe UI", 18, "bold"), fg="#a78bfa", bg="#0f172a")
        self.flu_score_lbl.pack()
        tk.Label(self.flu_card, text="Rhythm & Tempo", font=("Segoe UI", 8), fg=self.TEXT_MUTED, bg="#0f172a").pack()

        # Pitch Score Card
        self.pitch_card = tk.Frame(score_row, bg="#0f172a", padx=12, pady=8, highlightthickness=1, highlightbackground="#334155")
        self.pitch_card.pack(side="left", fill="both", expand=True)
        tk.Label(self.pitch_card, text="INTONATION", font=("Segoe UI", 8, "bold"), fg=self.TEXT_MUTED, bg="#0f172a").pack()
        self.pitch_score_lbl = tk.Label(self.pitch_card, text="-- %", font=("Segoe UI", 18, "bold"), fg="#f59e0b", bg="#0f172a")
        self.pitch_score_lbl.pack()
        tk.Label(self.pitch_card, text="Pitch Contour", font=("Segoe UI", 8), fg=self.TEXT_MUTED, bg="#0f172a").pack()

        # Per-Word Detailed Feedback Tiles Container
        tk.Label(right_col, text="Word-by-Word Alignment & Feedback:", font=("Segoe UI", 9, "bold"), fg=self.TEXT_LIGHT, bg=self.PANEL_BG).pack(anchor="w", pady=(4, 2))
        self.word_tiles_frame = tk.Frame(right_col, bg=self.PANEL_BG)
        self.word_tiles_frame.pack(fill="x", pady=(0, 8))
        self._render_placeholder_word_tiles()

        # Embedded Matplotlib Canvas for Waveforms & Pitch Contour
        tk.Label(right_col, text="Acoustic Comparison (Waveform & F0 Pitch Contour):", font=("Segoe UI", 9, "bold"), fg=self.TEXT_LIGHT, bg=self.PANEL_BG).pack(anchor="w", pady=(2, 2))
        self.plot_frame = tk.Frame(right_col, bg="#0f172a", highlightthickness=1, highlightbackground="#334155")
        self.plot_frame.pack(fill="both", expand=True)

        self._init_empty_plot()

    def _build_status_bar(self) -> None:
        """Bottom status bar with microphone and system status."""
        self.status_bar = tk.Frame(self.root, bg="#020617", padx=14, pady=4)
        self.status_bar.pack(side="bottom", fill="x")

        mic_ok = has_microphone()
        mic_text = "🎤 Microphone: Connected" if mic_ok else "⚠️ Microphone: Not Detected"
        mic_color = "#10b981" if mic_ok else "#ef4444"

        self.mic_status_lbl = tk.Label(self.status_bar, text=mic_text, font=("Segoe UI", 8), fg=mic_color, bg="#020617")
        self.mic_status_lbl.pack(side="left")

        self.system_status_lbl = tk.Label(self.status_bar, text="Ready", font=("Segoe UI", 8), fg=self.TEXT_MUTED, bg="#020617")
        self.system_status_lbl.pack(side="right")

    def _init_empty_plot(self) -> None:
        """Initialize empty waveform/pitch canvas."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.2, 3.6), dpi=100)
        fig.patch.set_facecolor("#1e293b")
        for ax in (ax1, ax2):
            ax.set_facecolor("#0f172a")
            ax.tick_params(colors="#64748b", labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#334155")
            ax.grid(True, linestyle="--", alpha=0.3, color="#334155")

        ax1.set_title("Waveform Alignment (Reference vs Learner)", color="#f8fafc", fontsize=9, fontweight="bold", pad=4)
        ax1.text(0.5, 0.5, "Record an attempt to visualize waveform", color="#64748b", ha="center", va="center")
        ax1.set_ylabel("Amplitude", color="#94a3b8", fontsize=8)

        ax2.set_title("Pitch Contour & Intonation (F0 Hz)", color="#f8fafc", fontsize=9, fontweight="bold", pad=4)
        ax2.text(0.5, 0.5, "Pitch intonation curves will appear here", color="#64748b", ha="center", va="center")
        ax2.set_xlabel("Time (s)", color="#94a3b8", fontsize=8)
        ax2.set_ylabel("Hz", color="#94a3b8", fontsize=8)

        plt.tight_layout()

        self.fig = fig
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _render_placeholder_word_tiles(self) -> None:
        """Render initial placeholder word feedback tiles."""
        for widget in self.word_tiles_frame.winfo_children():
            widget.destroy()

        tile = tk.Frame(self.word_tiles_frame, bg="#0f172a", padx=10, pady=6, highlightthickness=1, highlightbackground="#334155")
        tile.pack(side="left", padx=4, pady=2)
        tk.Label(tile, text="No attempt yet", font=("Segoe UI", 9, "italic"), fg=self.TEXT_MUTED, bg="#0f172a").pack()

    # ------------------- Event Handlers -------------------

    def _on_language_change(self, event=None) -> None:
        selected_name = self.lang_var.get()
        self.current_language_code = self.lang_codes.get(selected_name, "es")
        app_logger.info(f"Language changed to: {selected_name} ({self.current_language_code})")
        self._reload_lesson_queue()
        self._display_current_item()
        self._update_streak_badge()

    def _on_category_change(self, event=None) -> None:
        self.current_category = self.cat_var.get().lower()
        app_logger.info(f"Category changed to: {self.current_category}")
        self._reload_lesson_queue()
        self._display_current_item()

    def _on_mode_change(self, event=None) -> None:
        mode_label = self.mode_var.get()
        self.current_mode = self.mode_map.get(mode_label, "single_word")
        app_logger.info(f"Practice mode changed to: {self.current_mode}")

        if self.current_mode == "timed_quiz":
            self._start_timed_quiz()
        else:
            self.is_quiz_active = False
            self._reload_lesson_queue()
            self._display_current_item()

    def _reload_lesson_queue(self) -> None:
        """Load items adaptively based on language, category, and mode."""
        item_type = "word" if self.current_mode == "single_word" else ("phrase" if self.current_mode == "phrase" else None)
        self.current_queue = self.progress_tracker.get_adaptive_practice_queue(
            language=self.current_language_code,
            category=self.current_category,
            item_type=item_type
        )
        self.current_index = 0

    def _display_current_item(self) -> None:
        """Display the active lesson item in the UI card."""
        if not self.current_queue:
            self._show_banner("No lesson items found for this selection.", "warning")
            return

        item = self.current_queue[self.current_index]

        # Reset audio states
        self.current_ref_audio_path = None
        self.current_learner_audio_path = None
        self.current_comparison = None

        # Mode tag & progress
        if self.is_quiz_active:
            self.mode_pill.config(text=f"QUIZ: {self.quiz_index + 1} OF {len(self.quiz_items)}", bg="#7c3aed", fg="#ffffff")
            self.item_counter_lbl.config(text=f"Score: {np.mean(self.quiz_scores):.0f}%" if self.quiz_scores else "Quiz in progress")
        else:
            self.mode_pill.config(text=item.item_type.upper(), bg="#0c4a6e", fg="#38bdf8")
            self.item_counter_lbl.config(text=f"Item {self.current_index + 1} of {len(self.current_queue)}")

        # Spaced repetition status pill
        mastery_dict = self.db.get_word_mastery_dict(self.current_language_code)
        m = mastery_dict.get(item.target_text)
        if not m:
            self.mastery_pill.config(text="UNSEEN", bg="#334155", fg="#94a3b8")
        elif m["is_mastered"] == 1:
            self.mastery_pill.config(text="MASTERED ✓", bg="#065f46", fg="#34d399")
        elif m["avg_score"] < 65:
            self.mastery_pill.config(text="NEEDS PRACTICE", bg="#7f1d1d", fg="#f87171")
        else:
            self.mastery_pill.config(text="LEARNING", bg="#78350f", fg="#fbbf24")

        # Texts
        self.target_text_lbl.config(text=item.target_text)
        self.roman_lbl.config(text=f"[{item.romanization}] • {item.phonetic_guide}")
        self.trans_lbl.config(text=item.translation)
        self.tip_lbl.config(text=item.tips)

        # Reset scores to pending
        self.overall_score_lbl.config(text="-- %", fg="#94a3b8")
        self.grade_pill.config(text="Pending", bg="#1e293b", fg="#94a3b8")
        self.acc_score_lbl.config(text="-- %")
        self.flu_score_lbl.config(text="-- %")
        self.pitch_score_lbl.config(text="-- %")

        self.action_tips_lbl.config(text="Record an attempt to see targeted feedback on specific sounds.", fg=self.TEXT_MUTED)
        self._render_placeholder_word_tiles()
        self._show_banner("Click 'Listen Reference' to hear correct pronunciation.", "info")

    def _next_item(self) -> None:
        """Advance to next item."""
        if self.is_quiz_active:
            self.quiz_index += 1
            if self.quiz_index < len(self.quiz_items):
                self.current_queue = self.quiz_items
                self.current_index = self.quiz_index
                self._display_current_item()
            else:
                self._finish_quiz()
            return

        if self.current_queue and self.current_index < len(self.current_queue) - 1:
            self.current_index += 1
            self._display_current_item()
        elif self.current_queue:
            self.current_index = 0
            self._display_current_item()

    def _prev_item(self) -> None:
        """Return to previous item."""
        if self.is_quiz_active:
            return  # Prev disabled in quiz
        if self.current_queue and self.current_index > 0:
            self.current_index -= 1
            self._display_current_item()

    def _shuffle_queue(self) -> None:
        """Shuffle practice items."""
        if not self.is_quiz_active and self.current_queue:
            import random
            random.shuffle(self.current_queue)
            self.current_index = 0
            self._display_current_item()
            self._show_banner("Shuffled lesson queue.", "info")

    # ------------------- Audio Actions & Threading -------------------

    def _play_reference_audio(self) -> None:
        """Download/retrieve reference audio and play in background thread."""
        if not self.current_queue:
            return

        item = self.current_queue[self.current_index]
        self.btn_listen.config(text="⏳ Fetching Audio...", state="disabled")
        self._show_banner("Fetching reference audio...", "info")

        def _worker():
            try:
                wav_path = self.ref_audio_service.get_or_generate(
                    language=self.current_language_code,
                    text=item.target_text
                )
                self.current_ref_audio_path = wav_path

                def _on_finish():
                    self.root.after(0, lambda: self.btn_listen.config(text="🔊 Listen Reference", state="normal"))
                    self.root.after(0, lambda: self._show_banner("Reference audio playback finished.", "info"))

                self.root.after(0, lambda: self.btn_listen.config(text="🔊 Playing..."))
                self.ref_audio_service.play(wav_path, on_finish=_on_finish)

            except NetworkUnavailableError as net_err:
                self.root.after(0, lambda: self._handle_network_error(str(net_err)))
            except Exception as e:
                self.root.after(0, lambda: self._show_banner(f"Error loading reference audio: {e}", "danger"))
            finally:
                if not self.ref_audio_service.is_playing:
                    self.root.after(0, lambda: self.btn_listen.config(text="🔊 Listen Reference", state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_recording(self) -> None:
        """Start or stop audio recording."""
        if self.recorder.is_recording:
            self._stop_and_evaluate_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """Start voice recording with live VU meter feedback."""
        if not has_microphone():
            self._show_banner("No microphone detected! Please connect an audio input device.", "danger")
            messagebox.showerror(
                "Microphone Not Found",
                "No microphone was detected on your system.\nPlease connect a microphone and restart the application."
            )
            return

        # Ensure reference playback is stopped
        self.ref_audio_service.stop()

        def _vu_callback(level: float):
            # Scale 0..1 to 0..100
            val = level * 100.0
            self.root.after(0, lambda: self._vu_meter_val.set(val))

        try:
            self.recorder.start_recording(level_callback=_vu_callback)
            self.btn_record.config(text="⏹️ Stop & Evaluate", style="Danger.TButton")
            self.rec_status_lbl.config(text="🔴 Recording... Speak now!", fg=self.ACCENT_RED)
            self._show_banner("Listening... Speak the target word or phrase clearly.", "info")
            self._record_start_time = time.time()
        except AudioRecordingError as err:
            self._show_banner(str(err), "danger")
        except Exception as e:
            self._show_banner(f"Recording start failed: {e}", "danger")

    def _stop_and_evaluate_recording(self) -> None:
        """Stop recording and trigger comparison & scoring in a background thread."""
        self.btn_record.config(text="⏳ Processing...", state="disabled")
        self.rec_status_lbl.config(text="Evaluating audio...", fg=self.ACCENT_CYAN)
        self._show_banner("Analyzing pronunciation, phonetics, and pitch contour...", "info")

        def _eval_worker():
            try:
                rec_path = self.recorder.stop_recording()
                self.current_learner_audio_path = rec_path

                # Check for silence
                if AudioRecorder.check_silence(rec_path):
                    self.root.after(0, lambda: self._handle_silence_error())
                    return

                # Ensure reference audio is ready for comparison
                item = self.current_queue[self.current_index]
                if not self.current_ref_audio_path or not self.current_ref_audio_path.exists():
                    try:
                        self.current_ref_audio_path = self.ref_audio_service.get_or_generate(
                            language=self.current_language_code,
                            text=item.target_text
                        )
                    except Exception:
                        pass

                # Transcribe
                transcription = ""
                try:
                    transcription = self.recorder.transcribe(rec_path, language=self.current_language_code)
                except SpeechRecognitionFailedError as sr_err:
                    self.root.after(0, lambda: self._handle_transcription_error(str(sr_err)))
                    return
                except NetworkUnavailableError as net_err:
                    self.root.after(0, lambda: self._handle_network_error(str(net_err)))
                    return

                # Compare
                comparison = self.comparator.compare(
                    target_text=item.target_text,
                    recognized_text=transcription,
                    language=self.current_language_code,
                    ref_audio_path=self.current_ref_audio_path,
                    learner_audio_path=self.current_learner_audio_path
                )
                self.current_comparison = comparison

                # Score & Feedback
                score_obj = self.scorer.evaluate(
                    comparison=comparison,
                    language=self.current_language_code,
                    romanization=item.romanization
                )
                self.current_score = score_obj

                # Record in Database
                attempt_id = self.db.record_attempt(
                    language=self.current_language_code,
                    category=self.current_category,
                    mode=self.current_mode,
                    target_text=item.target_text,
                    transcribed_text=transcription,
                    accuracy_score=score_obj.accuracy_score,
                    fluency_score=score_obj.fluency_score,
                    rhythm_score=score_obj.rhythm_score,
                    pitch_score=score_obj.pitch_score,
                    overall_score=score_obj.overall_score,
                    audio_path=str(rec_path),
                    feedback=score_obj.to_dict()
                )

                # Update UI on main thread
                self.root.after(0, lambda: self._apply_evaluation_results(score_obj, comparison, transcription))

            except Exception as e:
                app_logger.error(f"Evaluation error: {e}", exc_info=True)
                self.root.after(0, lambda: self._show_banner(f"Evaluation failed: {e}", "danger"))
            finally:
                self.root.after(0, lambda: self._reset_record_btn())

        threading.Thread(target=_eval_worker, daemon=True).start()

    def _reset_record_btn(self) -> None:
        self.btn_record.config(text="🎤 Record My Attempt", style="Success.TButton", state="normal")
        self.rec_status_lbl.config(text="Ready to record", fg=self.TEXT_MUTED)
        self._vu_meter_val.set(0.0)

    def _apply_evaluation_results(
        self,
        score: PronunciationScore,
        comparison: ComparisonResult,
        transcription: str
    ) -> None:
        """Render evaluation scores, color-coded word tiles, and comparison plot."""
        # 1. Update Score Cards
        self.overall_score_lbl.config(text=f"{score.overall_score:.0f}%", fg=score.grade_color)
        self.grade_pill.config(text=score.grade, bg=score.grade_color, fg="#ffffff")
        self.acc_score_lbl.config(text=f"{score.accuracy_score:.0f}%")
        self.flu_score_lbl.config(text=f"{score.fluency_score:.0f}%")
        self.pitch_score_lbl.config(text=f"{score.pitch_score:.0f}%")

        # 2. Update Banner with Transcribed Text
        msg = f"Recognized: \"{transcription}\" — {score.summary}"
        self._show_banner(msg, "success" if score.overall_score >= 70 else "warning")

        # 3. Update Actionable Tips
        tips_text = "\n".join(score.actionable_tips)
        self.action_tips_lbl.config(text=tips_text, fg=self.TEXT_LIGHT)

        # 4. Render Per-Word Feedback Tiles
        self._render_word_feedback_tiles(comparison.word_feedback)

        # 5. Render Comparison Plot
        self._render_comparison_plot(comparison)

        # 6. Update Streak Badge & Spaced Repetition Pill
        self._update_streak_badge()
        if score.is_mastery_level:
            self.mastery_pill.config(text="MASTERED ✓", bg="#065f46", fg="#34d399")

        # 7. If quiz active, store score
        if self.is_quiz_active:
            self.quiz_scores.append(score.overall_score)

    def _render_word_feedback_tiles(self, word_feedbacks: List[Any]) -> None:
        """Draw interactive color-coded feedback chips for each word."""
        for widget in self.word_tiles_frame.winfo_children():
            widget.destroy()

        if not word_feedbacks:
            self._render_placeholder_word_tiles()
            return

        for wf in word_feedbacks:
            # Color based on status
            if wf.status == "correct":
                bg_c = "#065f46"
                fg_c = "#34d399"
                badge = "✓ Correct"
            elif wf.status == "close":
                bg_c = "#78350f"
                fg_c = "#fbbf24"
                badge = "~ Close"
            elif wf.status == "mispronounced":
                bg_c = "#7f1d1d"
                fg_c = "#f87171"
                badge = "✗ Check Sound"
            else:  # missing
                bg_c = "#334155"
                fg_c = "#94a3b8"
                badge = "∅ Missing"

            tile = tk.Frame(self.word_tiles_frame, bg=bg_c, padx=8, pady=4, highlightthickness=1, highlightbackground="#475569")
            tile.pack(side="left", padx=4, pady=2)

            tk.Label(tile, text=wf.word, font=("Segoe UI", 10, "bold"), fg="#ffffff", bg=bg_c).pack()
            badge_lbl = tk.Label(tile, text=f"{badge} ({wf.similarity*100:.0f}%)", font=("Segoe UI", 7, "bold"), fg=fg_c, bg=bg_c)
            badge_lbl.pack()

            # Tooltip click/hover
            tile.bind("<Button-1>", lambda e, tip=wf.tip: self._show_banner(tip, "info"))

    def _render_comparison_plot(self, comparison: ComparisonResult) -> None:
        """Render updated waveforms and pitch contour overlay into the canvas."""
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        fig = self.comparator.generate_comparison_plot(comparison, dark_theme=True)
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------- Error Handlers & Banners -------------------

    def _show_banner(self, text: str, alert_type: str = "info") -> None:
        """Display styled banner message."""
        color_map = {
            "info": ("#1e3a8a", "#60a5fa"),       # Blue
            "success": ("#064e3b", "#34d399"),    # Green
            "warning": ("#78350f", "#fbbf24"),    # Amber
            "danger": ("#7f1d1d", "#f87171"),     # Red
        }
        bg, fg = color_map.get(alert_type, ("#334155", "#f8fafc"))
        self.banner_frame.config(bg=bg)
        self.banner_lbl.config(text=text, bg=bg, fg=fg)

    def _handle_network_error(self, message: str) -> None:
        """Clear guidance when an operation requires an internet connection."""
        self._show_banner("Network Required: Please check your internet connection.", "warning")
        messagebox.showwarning(
            "Internet Connection Required",
            f"{message}\n\nPlease check your internet connection and try again."
        )

    def _handle_silence_error(self) -> None:
        """Clear guidance when recorded audio is silent."""
        self._show_banner("No speech detected (silent recording). Please speak clearly into the microphone.", "warning")
        self.action_tips_lbl.config(
            text="• Ensure your microphone is positioned close to you.\n• Speak clearly at a moderate volume.",
            fg="#fbbf24"
        )

    def _handle_transcription_error(self, message: str) -> None:
        """Clear guidance when speech cannot be recognized."""
        self._show_banner(f"Could not recognize words clearly. Listen to reference and try again.", "warning")
        self.action_tips_lbl.config(
            text=f"• {message}\n• Tip: Break down each syllable and match the speaker's speed.",
            fg="#fbbf24"
        )

    # ------------------- Timed Quiz Mode -------------------

    def _start_timed_quiz(self) -> None:
        """Initialize 10-word random timed quiz session."""
        try:
            self.quiz_items = self.lesson_bank.get_quiz_items(
                language=self.current_language_code,
                category=self.current_category,
                count=10
            )
            self.is_quiz_active = True
            self.quiz_index = 0
            self.quiz_scores = []
            self.current_queue = self.quiz_items
            self.current_index = 0
            self._display_current_item()
            self._show_banner("Timed Quiz Started! Complete all 10 words for your final mastery evaluation.", "info")
        except Exception as e:
            self._show_banner(f"Failed to start quiz: {e}", "danger")

    def _finish_quiz(self) -> None:
        """Conclude the quiz and present summary dialog."""
        self.is_quiz_active = False
        avg_score = float(np.mean(self.quiz_scores)) if self.quiz_scores else 0.0
        passed = sum(1 for s in self.quiz_scores if s >= 70.0)

        # Record quiz session
        self.db.record_quiz_session(
            language=self.current_language_code,
            category=self.current_category,
            total_items=len(self.quiz_items),
            average_score=round(avg_score, 1),
            passed_count=passed
        )

        grade, color = self.scorer.get_grade_info(avg_score)
        summary_msg = (
            f"Quiz Completed!\n\n"
            f"Language: {self.lang_var.get()}\n"
            f"Category: {self.cat_var.get()}\n"
            f"Average Score: {avg_score:.1f}%\n"
            f"Final Grade: {grade}\n"
            f"Passed Words: {passed} of {len(self.quiz_items)}\n\n"
            f"Keep practicing to increase your fluency and category mastery!"
        )
        messagebox.showinfo("Quiz Evaluation Summary", summary_msg)

        # Revert to single word mode
        self.mode_var.set("Single Word")
        self._on_mode_change()

    # ------------------- Mastery Modal & PDF Export -------------------

    def _update_streak_badge(self) -> None:
        """Update top bar streak count."""
        streak_info = self.db.get_streak_info()
        count = streak_info["current_streak"]
        self.streak_badge.config(text=f"🔥 Streak: {count} Days")

    def _show_mastery_modal(self) -> None:
        """Open detailed curriculum mastery overview window."""
        modal = tk.Toplevel(self.root)
        modal.title(f"Mastery Dashboard — {self.lang_var.get()}")
        modal.geometry("640x520")
        modal.configure(bg=self.BG_COLOR)
        modal.transient(self.root)

        tk.Label(modal, text=f"Curriculum Mastery: {self.lang_var.get()}", font=("Segoe UI", 14, "bold"), fg=self.TEXT_LIGHT, bg=self.BG_COLOR).pack(pady=(16, 8))

        stats = self.progress_tracker.get_category_mastery_stats(self.current_language_code)

        for cat_name, c_data in stats.items():
            card = tk.Frame(modal, bg=self.PANEL_BG, padx=12, pady=10, highlightthickness=1, highlightbackground=self.BORDER_COLOR)
            card.pack(fill="x", padx=16, pady=4)

            top_row = tk.Frame(card, bg=self.PANEL_BG)
            top_row.pack(fill="x")
            tk.Label(top_row, text=cat_name.capitalize(), font=("Segoe UI", 11, "bold"), fg=self.TEXT_LIGHT, bg=self.PANEL_BG).pack(side="left")
            pct_lbl = tk.Label(top_row, text=f"{c_data['mastery_percentage']}% Mastered", font=("Segoe UI", 10, "bold"), fg=self.ACCENT_CYAN, bg=self.PANEL_BG)
            pct_lbl.pack(side="right")

            # Progress Bar
            pbar = ttk.Progressbar(card, maximum=100, value=c_data["mastery_percentage"])
            pbar.pack(fill="x", pady=(4, 4))

            details = f"Words Mastered: {c_data['mastered_items']}/{c_data['total_items']}  |  Attempted: {c_data['attempted_items']}  |  Avg Score: {c_data['average_score']}%"
            tk.Label(card, text=details, font=("Segoe UI", 8), fg=self.TEXT_MUTED, bg=self.PANEL_BG).pack(anchor="w")

        btn_close = ttk.Button(modal, text="Close Dashboard", style="Primary.TButton", command=modal.destroy)
        btn_close.pack(pady=16)

    def _export_pdf_report(self) -> None:
        """Generate and prompt opening of progress PDF report."""
        try:
            pdf_path = self.report_generator.generate_pdf(
                language=self.current_language_code,
                language_name=self.lang_var.get()
            )
            ans = messagebox.askyesno(
                "PDF Report Generated",
                f"Your progress report has been saved to:\n{pdf_path}\n\nWould you like to open it now?"
            )
            if ans:
                webbrowser.open(str(pdf_path.resolve()))
        except Exception as e:
            app_logger.error(f"PDF generation failed: {e}", exc_info=True)
            messagebox.showerror("Export Failed", f"Could not generate PDF report: {e}")

    def _on_close(self) -> None:
        """Safely release audio resources and exit."""
        self.ref_audio_service.stop()
        if self.recorder.is_recording:
            try:
                self.recorder.stop_recording()
            except Exception:
                pass
        self.root.destroy()
