# 🗣️ Pronunciation Trainer

A desktop speech coaching application built with Python 3.10+ and Tkinter. **Pronunciation Trainer** helps language learners master pronunciation, accent nuances, rhythm, and intonation across multiple languages through multi-modal acoustic analysis, phonetic alignment, spaced repetition, and visual feedback.

---

## 🌟 Features

- **Multi-Language Support**:
  - 🇪🇸 **Spanish** (`es`)
  - 🇫🇷 **French** (`fr`)
  - 🇮🇳 **Hindi** (`hi`)
  - 🇮🇳 **Tamil** (`ta`)
  - 🇩🇪 **German** (`de`)
  - 🇯🇵 **Japanese** (`ja`)
- **Curated Lesson Bank**:
  - 5 Core Categories: **Greetings**, **Numbers**, **Travel**, **Food**, **Business**.
  - 3 Difficulty Levels: Beginner, Intermediate, and Advanced.
  - Native script, romanization / transliteration, English translations, phonetic guides, and pronunciation tips.
- **Reference Audio (gTTS) with Smart Caching**:
  - Synthesizes reference audio using Google Text-to-Speech.
  - Automatically caches reference WAV/MP3 files locally in `recordings/reference/`.
  - Once cached, practice rounds work completely offline without requiring internet.
  - Graceful network detection with clear prompts if an uncached word is requested offline.
- **Microphone Recording with Live VU Metering**:
  - Non-blocking audio capture with real-time VU meter showing input volume.
  - Automatic silence detection to prevent evaluating silent or accidental recordings.
  - Hardware microphone autodetection.
- **Multi-Modal Comparison Engine**:
  - **Textual & Phonetic Alignment**: Levenshtein distance and dynamic programming token alignment to evaluate word-by-word pronunciation accuracy.
  - **Acoustic & Prosodic Analysis (Librosa)**:
    - Waveform duration and envelope comparison.
    - Fundamental frequency ($F_0$) pitch contour tracking via YIN algorithm.
    - Key-invariant pitch contour overlay (evaluates intonation slope regardless of male vs female vocal register).
    - Rhythm and tempo correlation.
- **Actionable Per-Word Feedback**:
  - Color-coded visual badges:
    - 🟩 **Correct** (score $\ge 85\%$)
    - 🟨 **Close** ($60\% - 84\%$)
    - 🟥 **Check Sound** ($< 60\%$)
    - ⬜ **Missing / Omitted**
  - Interactive click-to-view specific phonetic tips for problem words.
- **Adaptive Spaced-Repetition**:
  - Low-scoring words repeat more frequently in the practice queue.
  - Mastered words ($\ge 85\%$ across consecutive attempts) graduate out of immediate rotation.
- **Daily Streak Tracker & Mastery Dashboard**:
  - Consecutive day practice streak counter with fire badge (`🔥 Streak: X Days`).
  - Mastery Dashboard calculating % curriculum mastered per category with visual progress bars.
- **3 Practice Modes**:
  1. **Single Word Practice**: Drill vocabulary and isolated sounds.
  2. **Phrase Practice**: Master conversational flow, liaisons, and connected speech.
  3. **Timed Quiz Mode**: 10 randomized words/phrases with a cumulative score evaluation and pass/fail summary.
- **Professional PDF Report Export**:
  - Formatted PDF progress reports created via ReportLab and Matplotlib.
  - Includes learner streak statistics, category breakdown table, score trend chart, and recent attempt logs.
- **Threaded GUI Architecture**:
  - All network downloads, audio playback, recording, and signal processing run in background worker threads so the Tkinter UI remains smooth and responsive.

---

## 📂 Project Structure

```
pronunciation_trainer/
├── main.py                     # Tkinter GUI application entry point
├── verify_round.py             # End-to-end verification and pipeline test script
├── requirements.txt            # Package dependencies
├── README.md                   # Setup guide and documentation
├── trainer/
│   ├── gui.py                  # Tkinter UI controller with custom dark theme
│   ├── lesson_bank.py          # Lesson curriculum across 6 languages & 5 categories
│   ├── reference_audio.py      # gTTS reference generation, local caching & playback
│   ├── recorder.py             # Microphone recording, VU metering, speech recognition
│   ├── comparator.py           # Levenshtein alignment & Librosa acoustic/pitch comparator
│   ├── scorer.py               # Multi-modal scoring, grading, and actionable tips
│   ├── progress.py             # Spaced-repetition scheduler & mastery analytics
│   ├── database.py             # SQLite persistence: attempts, streaks, word mastery
│   ├── report.py               # ReportLab PDF progress report generation
│   └── logger.py               # Thread-safe logging and custom exception hierarchy
├── recordings/                 # Saved learner attempts and cached reference audio
├── outputs/                    # Exported PDF progress reports and waveform plots
├── logs/                       # Rotating application logs
├── data/                       # SQLite database file (pronunciation_trainer.db)
└── tests/
    └── test_comparator.py      # Unit & integration tests for all components
```

---

## 🚀 Installation & Setup

### Prerequisites
- **Python**: Version 3.10, 3.11, 3.12, 3.13, or 3.14+.
- **Microphone**: Any standard USB or built-in audio input device.
- **Internet Connection**: Required for first-time reference audio downloads and Google Speech Recognition (cached audio functions offline).

### 1. Clone or Navigate to Project
```bash
cd pronunciation_trainer
```

### 2. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

> **Note on Windows / Audio Drivers**:
> `sounddevice` and `soundfile` are bundled with precompiled PortAudio and libsndfile binaries, ensuring immediate recording and playback capability on Windows out of the box without needing Visual Studio C++ build tools.

---

## 🎮 Running the Application

Launch the desktop application:
```bash
python main.py
```

### Practice Workflow:
1. Select your target **Language** (e.g. *Spanish*, *French*, *Hindi*, *Tamil*, *German*, *Japanese*) from the top bar.
2. Select a **Category** (e.g. *Greetings*, *Food*, *Travel*, etc.).
3. Choose your **Mode** (*Single Word*, *Phrase*, or *Timed Quiz*).
4. Click **🔊 Listen Reference** to hear native pronunciation.
5. Click **🎤 Record My Attempt**, speak the phrase into your microphone, then click **⏹️ Stop & Evaluate**.
6. Review your scores:
   - **Overall Score** and letter grade card.
   - **Word-by-word** feedback tiles with color coding.
   - **Waveform Alignment** (Reference in cyan, Learner in mint green).
   - **Pitch Contour (F0)** intonation overlay curve.
7. Click **📊 Mastery Dashboard** to inspect curriculum completion percentages.
8. Click **📄 Export PDF Report** to generate and open a formatted progress report.

---

## 🧪 Running the Test Suite

Run the automated pytest suite:
```bash
python -m pytest tests/test_comparator.py -v
```

Run the end-to-end simulation verification script:
```bash
python verify_round.py
```

---

## 🔧 Troubleshooting Guide

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Microphone: Not Detected"** | Audio input device is disconnected or blocked in OS privacy settings. | Connect a microphone and check Windows Settings -> Privacy & Security -> Microphone to allow desktop apps access. |
| **"No speech detected (silent recording)"** | Microphone input volume is muted or recording threshold was too low. | Check the live green VU meter bar while speaking. Increase microphone gain in your OS sound settings. |
| **"Network Required: Please check your internet connection"** | gTTS or Speech Recognition requested while offline for an uncached item. | Connect to Wi-Fi. Items that were previously synthesized are stored in `recordings/reference/` and will play offline. |
| **"Speech recognition service unreachable"** | DNS or firewall blocking Google Speech API endpoints. | Verify internet connectivity and ensure port 443 / HTTPS traffic is permitted. |
| **Non-Latin Characters (Hindi, Tamil, Japanese)** | Font glyphs in Windows console or third-party PDF viewers. | The GUI and PDF generators automatically use UTF-8 and sanitized entity encodings to prevent encoding crashes. |

---

## ✅ Completion Checklist

- [x] Full Python 3.10+ Tkinter application architecture (`main.py` + `trainer/` modules).
- [x] 6 languages supported: Spanish, French, Hindi, Tamil, German, Japanese.
- [x] 5 lesson categories supported: Greetings, Numbers, Travel, Food, Business.
- [x] gTTS reference audio playback with offline caching and network error detection.
- [x] Non-blocking audio recorder with live VU meter and silence detection.
- [x] SpeechRecognition transcription with language-specific localization.
- [x] Levenshtein phonetic word alignment and per-word status classification.
- [x] Librosa acoustic prosody analysis: duration ratio, RMS rhythm correlation, YIN pitch contour ($F_0$).
- [x] Matplotlib dual-panel visualization embedded directly into Tkinter canvas.
- [x] Adaptive spaced-repetition difficulty: low scores repeat, mastered words graduate.
- [x] Daily streak tracker and curriculum mastery dashboard modal.
- [x] 3 practice modes: Single Word, Phrase, and 10-word Timed Quiz with summary dialog.
- [x] ReportLab PDF progress report export with embedded charts.
- [x] Custom exceptions, logging to console and rotating log file, thread safety.
- [x] 16 passing pytest unit and integration tests.
- [x] End-to-end verification script with validated score, plot, and PDF artifacts.
