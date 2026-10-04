"""Streamlit Web Interface for Pronunciation Trainer.

Enables learners to practice pronunciation directly in any browser with real-time
phonetic evaluation, waveform/pitch visualization, mastery tracking, and PDF reports.
"""

import sys
import tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import streamlit as st
import matplotlib.pyplot as plt

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trainer.logger import app_logger
from trainer.lesson_bank import LessonBank, LessonItem
from trainer.reference_audio import ReferenceAudioService
from trainer.recorder import AudioRecorder
from trainer.comparator import PronunciationComparator, ComparisonResult
from trainer.scorer import PronunciationScorer
from trainer.database import DatabaseManager
from trainer.progress import ProgressTracker
from trainer.report import ProgressReportGenerator

# Page config
st.set_page_config(
    page_title="Pronunciation Trainer",
    page_icon="🗣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stMetric { background-color: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #334155; }
    .target-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        margin-bottom: 20px;
    }
    .word-badge-correct {
        background-color: #065f46; color: #34d399; padding: 4px 8px;
        border-radius: 6px; font-weight: bold; margin: 4px; display: inline-block;
    }
    .word-badge-close {
        background-color: #78350f; color: #fbbf24; padding: 4px 8px;
        border-radius: 6px; font-weight: bold; margin: 4px; display: inline-block;
    }
    .word-badge-mis {
        background-color: #7f1d1d; color: #f87171; padding: 4px 8px;
        border-radius: 6px; font-weight: bold; margin: 4px; display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Initialize cached services
@st.cache_resource
def get_services():
    bank = LessonBank()
    db = DatabaseManager("data/pronunciation_trainer.db")
    progress = ProgressTracker(db, bank)
    ref_audio = ReferenceAudioService("recordings/reference")
    comparator = PronunciationComparator()
    scorer = PronunciationScorer()
    reporter = ProgressReportGenerator(db, progress, output_dir="outputs")
    return bank, db, progress, ref_audio, comparator, scorer, reporter

bank, db, progress, ref_audio, comparator, scorer, reporter = get_services()

# Sidebar: Controls & Navigation
with st.sidebar:
    st.title("🗣️ Pronunciation Trainer")
    st.caption("AI Speech & Prosody Coach")

    languages = bank.get_languages()
    lang_name = st.selectbox("Choose Language", options=list(languages.values()), index=0)
    lang_code = {v: k for k, v in languages.items()}[lang_name]

    categories = bank.get_categories()
    cat_name = st.selectbox("Category", options=[c.capitalize() for c in categories], index=0).lower()

    mode_options = ["Single Word", "Phrase", "Timed Quiz (10 Words)"]
    mode_selection = st.selectbox("Practice Mode", options=mode_options, index=0)
    mode_code = "single_word" if mode_selection == "Single Word" else ("phrase" if mode_selection == "Phrase" else "timed_quiz")

    # Daily Streak Badge
    streak_info = db.get_streak_info()
    st.markdown(f"### 🔥 Streak: **{streak_info['current_streak']} Days**")
    st.caption(f"Total active practice days: {streak_info['total_practice_days']}")

    st.markdown("---")

    # PDF Report Export
    st.subheader("📄 Export Progress")
    if st.button("Generate PDF Report", use_container_width=True):
        with st.spinner("Compiling PDF progress report..."):
            pdf_path = reporter.generate_pdf(lang_code, lang_name)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="⬇️ Download Progress PDF",
                data=pdf_bytes,
                file_name=pdf_path.name,
                mime="application/pdf",
                use_container_width=True
            )

# Load lesson items
if mode_code == "timed_quiz":
    if "quiz_items" not in st.session_state or st.session_state.get("quiz_lang") != lang_code:
        st.session_state.quiz_items = bank.get_quiz_items(lang_code, category=cat_name, count=10)
        st.session_state.quiz_idx = 0
        st.session_state.quiz_scores = []
        st.session_state.quiz_lang = lang_code
    items = st.session_state.quiz_items
    curr_idx = min(st.session_state.quiz_idx, len(items) - 1)
else:
    items = progress.get_adaptive_practice_queue(
        language=lang_code,
        category=cat_name,
        item_type="word" if mode_code == "single_word" else "phrase"
    )
    if "item_idx" not in st.session_state:
        st.session_state.item_idx = 0
    curr_idx = st.session_state.item_idx % len(items) if items else 0

if not items:
    st.warning("No lesson items found for this selection.")
    st.stop()

current_item: LessonItem = items[curr_idx]

# Check word mastery status
mastery_dict = db.get_word_mastery_dict(lang_code)
m_info = mastery_dict.get(current_item.target_text)
if not m_info:
    status_label, status_color = "UNSEEN", "#94a3b8"
elif m_info["is_mastered"] == 1:
    status_label, status_color = "MASTERED ✓", "#34d399"
elif m_info["avg_score"] < 65:
    status_label, status_color = "NEEDS PRACTICE", "#f87171"
else:
    status_label, status_color = "LEARNING", "#fbbf24"

# Main Layout
col_left, col_right = st.columns([1.1, 1.3], gap="large")

with col_left:
    # Target Word Card
    st.markdown(f"""
    <div class="target-card">
        <span style="background-color: #0c4a6e; color: #38bdf8; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">
            {current_item.level.upper()} • {current_item.item_type.upper()}
        </span>
        <span style="background-color: #334155; color: {status_color}; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-left: 8px;">
            {status_label}
        </span>
        <h1 style="color: #38bdf8; font-size: 44px; margin: 16px 0 8px 0;">{current_item.target_text}</h1>
        <p style="color: #f8fafc; font-size: 18px; font-style: italic; margin-bottom: 4px;">[{current_item.romanization}] • {current_item.phonetic_guide}</p>
        <p style="color: #94a3b8; font-size: 16px;">{current_item.translation}</p>
    </div>
    """, unsafe_allow_html=True)

    # Phonetic Tip
    st.info(f"💡 **Pronunciation Tip:** {current_item.tips}")

    # Reference Audio
    st.markdown("### 🔊 Reference Pronunciation")
    try:
        ref_path = ref_audio.get_or_generate(lang_code, current_item.target_text)
        with open(ref_path, "rb") as f:
            st.audio(f.read(), format="audio/wav")
    except Exception as e:
        st.warning(f"Could not load reference audio: {e}")
        ref_path = None

    # Learner Audio Input
    st.markdown("### 🎤 Record or Upload Your Attempt")
    learner_audio_input = st.audio_input("Record your voice")

    # Item Navigation
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("◀ Previous"):
            if mode_code == "timed_quiz":
                st.session_state.quiz_idx = max(0, st.session_state.quiz_idx - 1)
            else:
                st.session_state.item_idx = max(0, curr_idx - 1)
            st.rerun()
    with c2:
        if st.button("🔀 Shuffle"):
            import random
            st.session_state.item_idx = random.randint(0, len(items) - 1)
            st.rerun()
    with c3:
        if st.button("Next Item ▶"):
            if mode_code == "timed_quiz":
                st.session_state.quiz_idx = curr_idx + 1
            else:
                st.session_state.item_idx = curr_idx + 1
            st.rerun()

with col_right:
    st.markdown("### 📊 Pronunciation & Prosody Analysis")

    if learner_audio_input is not None:
        # Save temporary learner wav
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
            tmp_wav.write(learner_audio_input.read())
            tmp_wav_path = Path(tmp_wav.name)

        # Evaluate attempt
        with st.spinner("Transcribing and evaluating phonetics & pitch contour..."):
            try:
                # Transcribe
                recorder_service = AudioRecorder()
                transcription = recorder_service.transcribe(tmp_wav_path, language=lang_code)

                # Compare
                comp_result = comparator.compare(
                    target_text=current_item.target_text,
                    recognized_text=transcription,
                    language=lang_code,
                    ref_audio_path=ref_path,
                    learner_audio_path=tmp_wav_path
                )

                # Score
                score_res = scorer.evaluate(comp_result, language=lang_code, romanization=current_item.romanization)

                # Persist
                db.record_attempt(
                    language=lang_code,
                    category=cat_name,
                    mode=mode_code,
                    target_text=current_item.target_text,
                    transcribed_text=transcription,
                    accuracy_score=score_res.accuracy_score,
                    fluency_score=score_res.fluency_score,
                    rhythm_score=score_res.rhythm_score,
                    pitch_score=score_res.pitch_score,
                    overall_score=score_res.overall_score,
                    audio_path=str(tmp_wav_path),
                    feedback=score_res.to_dict()
                )

                # Display Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Overall Score", f"{score_res.overall_score:.0f}%", score_res.grade)
                m2.metric("Accuracy", f"{score_res.accuracy_score:.0f}%")
                m3.metric("Fluency & Timing", f"{score_res.fluency_score:.0f}%")
                m4.metric("Pitch / Intonation", f"{score_res.pitch_score:.0f}%")

                st.success(f"**Recognized:** \"{transcription}\" — {score_res.summary}")

                # Word Feedback Tiles
                st.markdown("#### Word-by-Word Alignment:")
                tiles_html = []
                for wf in comp_result.word_feedback:
                    if wf.status == "correct":
                        cls_name = "word-badge-correct"
                        symbol = "✓"
                    elif wf.status == "close":
                        cls_name = "word-badge-close"
                        symbol = "~"
                    else:
                        cls_name = "word-badge-mis"
                        symbol = "✗"
                    tiles_html.append(f'<span class="{cls_name}">{wf.word} {symbol} ({wf.similarity*100:.0f}%)</span>')
                st.markdown("".join(tiles_html), unsafe_allow_html=True)

                # Actionable Tips
                if score_res.actionable_tips:
                    st.markdown("#### 🎯 Personalized Coach Tips:")
                    for tip in score_res.actionable_tips:
                        st.markdown(tip)

                # Waveform & Pitch Contour Plots
                st.markdown("#### 🌊 Waveform & Pitch Contour (F0 Overlay):")
                fig = comparator.generate_comparison_plot(comp_result, dark_theme=True)
                st.pyplot(fig)
                plt.close(fig)

            except Exception as eval_err:
                st.warning(f"Audio evaluation note: {eval_err}")
    else:
        st.info("Record or upload your pronunciation attempt to inspect real-time phonetic scores, waveform alignment, and pitch intonation.")

    # Category Curriculum Mastery Breakdown
    st.markdown("---")
    st.markdown("### 🏆 Category Curriculum Mastery")
    cat_stats = progress.get_category_mastery_stats(lang_code)
    for c_name, c_data in cat_stats.items():
        st.write(f"**{c_name.capitalize()}** — {c_data['mastery_percentage']}% Mastered ({c_data['mastered_items']}/{c_data['total_items']} words)")
        st.progress(c_data["mastery_percentage"] / 100.0)
