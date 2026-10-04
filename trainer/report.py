"""PDF progress report generation service using ReportLab and Matplotlib."""

import datetime
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)

from trainer.database import DatabaseManager
from trainer.progress import ProgressTracker
from trainer.logger import app_logger


def sanitize_text_for_pdf(text: str) -> str:
    """
    Ensure text is safe for ReportLab Helvetica rendering by escaping HTML
    and replacing problematic control characters.
    """
    if not text:
        return ""
    # Basic XML entity escaping for ReportLab Paragraphs
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Ensure printable ascii/latin-1 or clean fallback to prevent Helvetica font glyph errors
    clean_chars = []
    for ch in safe:
        if ord(ch) < 256:
            clean_chars.append(ch)
        else:
            # Replace non-latin-1 characters with unicode representation to guarantee Helvetica rendering
            clean_chars.append(f"&#{ord(ch)};")
    return "".join(clean_chars)


class ProgressReportGenerator:
    """Generates PDF analytics reports illustrating pronunciation progress over time."""

    def __init__(
        self,
        db: DatabaseManager,
        progress_tracker: ProgressTracker,
        output_dir: str = "outputs"
    ):
        self.db = db
        self.progress_tracker = progress_tracker
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_chart_image(self, language: str, output_img_path: Path) -> bool:
        """Create a dual-chart visual (Category Mastery & Score Trend) for embedding in PDF."""
        try:
            attempts = self.db.get_attempts(limit=30, language=language)
            attempts.reverse()  # Chronological order
            stats = self.progress_tracker.get_category_mastery_stats(language)

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.8), dpi=150)
            fig.patch.set_facecolor("#ffffff")

            # 1. Category Mastery Bar Chart
            categories = list(stats.keys())
            pcts = [stats[c]["mastery_percentage"] for c in categories]
            bar_colors = ["#38bdf8", "#34d399", "#f59e0b", "#a78bfa", "#f43f5e"][:len(categories)]

            ax1.barh(categories, pcts, color=bar_colors, edgecolor="#e2e8f0", height=0.6)
            ax1.set_xlim(0, 100)
            ax1.set_xlabel("Mastery %", fontsize=8, color="#475569")
            ax1.set_title("Mastery by Category", fontsize=9, fontweight="bold", color="#1e293b")
            ax1.tick_params(labelsize=7, colors="#475569")
            ax1.grid(axis="x", linestyle="--", alpha=0.5)

            # 2. Score Trend Line Chart
            if attempts:
                scores = [a["overall_score"] for a in attempts]
                x_vals = range(1, len(scores) + 1)
                ax2.plot(x_vals, scores, marker="o", markersize=3, color="#0ea5e9", linewidth=1.5, label="Overall")
                if len(scores) > 1:
                    # Rolling average trend line
                    moving_avg = [sum(scores[max(0, i-2):i+1])/len(scores[max(0, i-2):i+1]) for i in range(len(scores))]
                    ax2.plot(x_vals, moving_avg, color="#10b981", linestyle="--", linewidth=1.2, label="Trend")
                ax2.set_ylim(0, 105)
                ax2.set_xlabel("Recent Attempts", fontsize=8, color="#475569")
                ax2.set_title("Pronunciation Score Trend", fontsize=9, fontweight="bold", color="#1e293b")
                ax2.legend(fontsize=6, loc="lower right")
            else:
                ax2.text(0.5, 0.5, "No practice attempts yet", ha="center", va="center", color="#94a3b8")
                ax2.set_title("Score Trend", fontsize=9, fontweight="bold", color="#1e293b")

            ax2.tick_params(labelsize=7, colors="#475569")
            ax2.grid(True, linestyle="--", alpha=0.5)

            plt.tight_layout()
            fig.savefig(str(output_img_path), dpi=150, bbox_inches="tight")
            plt.close(fig)
            return True
        except Exception as e:
            app_logger.error(f"Failed to generate report chart: {e}")
            return False

    def generate_pdf(
        self,
        language: str,
        language_name: str,
        output_file: Optional[Path] = None
    ) -> Path:
        """
        Generate a complete PDF progress report for the specified language.

        Returns:
            Path to the generated PDF.
        """
        if output_file is None:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"pronunciation_report_{language}_{ts}.pdf"

        app_logger.info(f"Generating PDF progress report for '{language_name}' -> {output_file}")

        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )

        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=15,
        )

        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )

        bold_cell_style = ParagraphStyle(
            "BoldCell",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f172a"),
        )

        elements = []

        # 1. Header Banner
        now_str = datetime.datetime.now().strftime("%B %d, %Y - %H:%M")
        elements.append(Paragraph("Pronunciation Trainer — Mastery Report", title_style))
        elements.append(Paragraph(f"Language: <b>{language_name}</b> | Generated: {now_str}", subtitle_style))

        # 2. Executive Metrics Summary Cards
        summary = self.progress_tracker.get_learner_dashboard_summary(language)
        summary_data = [
            [
                Paragraph("<b>Current Daily Streak</b>", body_style),
                Paragraph("<b>Total Active Days</b>", body_style),
                Paragraph("<b>Mastered Words</b>", body_style),
                Paragraph("<b>Average Score</b>", body_style),
            ],
            [
                Paragraph(f"<font size=14 color='#0284c7'><b>{summary['current_streak']} Days 🔥</b></font>", body_style),
                Paragraph(f"<font size=14 color='#0f172a'><b>{summary['total_practice_days']}</b></font>", body_style),
                Paragraph(f"<font size=14 color='#10b981'><b>{summary['words_mastered']} / {summary['total_words_in_curriculum']}</b></font>", body_style),
                Paragraph(f"<font size=14 color='#8b5cf6'><b>{summary['overall_avg_score']}%</b></font>", body_style),
            ]
        ]

        summary_table = Table(summary_data, colWidths=[130, 130, 135, 135])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 12))

        # 3. Category Mastery Breakdown Table
        elements.append(Paragraph("Curriculum Mastery by Category", heading_style))
        cat_stats = summary["category_breakdown"]
        cat_rows = [
            [
                Paragraph("<b>Category</b>", bold_cell_style),
                Paragraph("<b>Items in Bank</b>", bold_cell_style),
                Paragraph("<b>Practiced</b>", bold_cell_style),
                Paragraph("<b>Mastered</b>", bold_cell_style),
                Paragraph("<b>Mastery %</b>", bold_cell_style),
                Paragraph("<b>Avg Score</b>", bold_cell_style),
            ]
        ]
        for cat_name, c_data in cat_stats.items():
            cat_rows.append([
                Paragraph(cat_name.capitalize(), body_style),
                Paragraph(str(c_data["total_items"]), body_style),
                Paragraph(str(c_data["attempted_items"]), body_style),
                Paragraph(str(c_data["mastered_items"]), body_style),
                Paragraph(f"{c_data['mastery_percentage']}%", bold_cell_style),
                Paragraph(f"{c_data['average_score']}%", body_style),
            ])

        cat_table = Table(cat_rows, colWidths=[120, 80, 80, 80, 85, 85])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(cat_table)
        elements.append(Spacer(1, 10))

        # 4. Progress Visual Chart
        chart_img_path = self.output_dir / f"temp_chart_{language}.png"
        if self._generate_chart_image(language, chart_img_path):
            elements.append(Image(str(chart_img_path), width=530, height=205))
            elements.append(Spacer(1, 10))

        # 5. Recent Practice Log
        elements.append(Paragraph("Recent Practice Attempts", heading_style))
        recent_attempts = self.db.get_attempts(limit=8, language=language)
        if recent_attempts:
            log_rows = [
                [
                    Paragraph("<b>Time</b>", bold_cell_style),
                    Paragraph("<b>Category</b>", bold_cell_style),
                    Paragraph("<b>Target Word/Phrase</b>", bold_cell_style),
                    Paragraph("<b>Accuracy</b>", bold_cell_style),
                    Paragraph("<b>Fluency</b>", bold_cell_style),
                    Paragraph("<b>Score</b>", bold_cell_style),
                ]
            ]
            for att in recent_attempts:
                t_str = att["timestamp"][:16].replace("T", " ")
                score_val = att["overall_score"]
                color_code = "#10b981" if score_val >= 85 else ("#0ea5e9" if score_val >= 70 else "#ef4444")
                log_rows.append([
                    Paragraph(t_str, body_style),
                    Paragraph(att["category"].capitalize(), body_style),
                    Paragraph(sanitize_text_for_pdf(att["target_text"]), body_style),
                    Paragraph(f"{att['accuracy_score']}%", body_style),
                    Paragraph(f"{att['fluency_score']}%", body_style),
                    Paragraph(f"<font color='{color_code}'><b>{score_val}%</b></font>", body_style),
                ])

            log_table = Table(log_rows, colWidths=[95, 80, 195, 55, 55, 50])
            log_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(log_table)
        else:
            elements.append(Paragraph("No practice attempts recorded yet for this language.", body_style))

        elements.append(Spacer(1, 10))

        # 6. Actionable Recommendations
        rec_block = [
            Paragraph("<b>Actionable Recommendations</b>", bold_cell_style),
            Paragraph("• <b>Spaced Repetition:</b> Words scored below 70% are automatically scheduled for early review in practice rounds.", body_style),
            Paragraph("• <b>Rhythm & Prosody:</b> Use the waveform and pitch contour overlay to align your timing and intonation with the reference speaker.", body_style),
            Paragraph("• <b>Daily Habit:</b> Keep your daily streak active by practicing at least 5 minutes every day.", body_style),
        ]
        elements.append(KeepTogether(rec_block))

        # Build document
        doc.build(elements)

        # Cleanup temporary chart image
        if chart_img_path.exists():
            try:
                chart_img_path.unlink()
            except Exception:
                pass

        app_logger.info(f"PDF report built successfully: {output_file}")
        return output_file
