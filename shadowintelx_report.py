"""Dependency-free, printable performance report generation."""

from __future__ import annotations

import textwrap
import unicodedata
from datetime import datetime
from typing import Any


def _pdf_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "replace").decode("ascii")
    return normalized.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\r", " ").replace("\n", " ")


def _make_content(lines: list[str]) -> bytes:
    commands = []
    y = 748
    for index, line in enumerate(lines):
        font_size = 19 if index == 0 else 10
        commands.append(f"BT /F1 {font_size} Tf 52 {y} Td ({_pdf_text(line)}) Tj ET")
        y -= 22 if index == 0 else 15
    return "\n".join(commands).encode("ascii", "replace")


def build_pdf_report(display_name: str, report: dict[str, Any], generated_at: datetime | None = None) -> bytes:
    """Build a small multi-page PDF with no third-party PDF package."""
    generated = generated_at or datetime.now().astimezone()
    accuracy = report.get("accuracy")
    accuracy_text = f"{accuracy}%" if accuracy is not None else ("No accuracy-based rounds yet" if report.get("attempt_count") else "No saved data yet")
    lines = [
        "ShadowIntelX IQ - Performance Intelligence",
        f"Student profile: {display_name}",
        f"Generated: {generated.strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "OVERVIEW",
        f"Completed saved rounds: {report.get('attempt_count', 0)}",
        f"Overall saved-round accuracy: {accuracy_text}",
        f"Average completion time: {report.get('average_duration') if report.get('average_duration') is not None else 'No data'} seconds",
        f"XP earned from saved rounds: {report.get('xp_earned', 0)}",
        "",
        "SKILL DNA (normalized arena scores from saved attempts)",
    ]
    profile = report.get("profile") or {}
    for item in profile.values():
        accuracy = item.get("accuracy")
        value = f"{accuracy}% across {item.get('attempts', 0)} rounds" if accuracy is not None else "No saved attempts yet"
        lines.append(f"{item.get('label', 'Skill')}: {value}")
    lines.extend(["", "PERFORMANCE NOTES"])
    strongest, weakest = report.get("strongest"), report.get("weakest")
    lines.append(f"Current strongest practiced area: {strongest['label']} ({strongest['recent_accuracy']}%)" if strongest else "Strengths: Not enough saved performance data yet.")
    lines.append(f"Area to practice next: {weakest['label']} ({weakest['recent_accuracy']}%)" if weakest else "Next step: Complete a practice round to create a baseline.")
    recommendation = report.get("recommendation")
    if recommendation:
        lines.append(f"Coach explanation: {recommendation['explanation']}")
        lines.append(f"Suggested exercise: {recommendation['exercise']}")
    lines.extend(["", "RECENT COMPLETED ROUNDS"])
    recent = list(report.get("recent") or [])[-20:]
    if not recent:
        lines.append("No completed rounds have been saved for this profile yet.")
    else:
        for row in reversed(recent):
            lines.append(
                f"{row.get('completed_at', '')[:16]} | {row.get('arena', 'Practice')} | {row.get('level', '')} | "
                f"{row.get('accuracy', 0):g}% | {row.get('duration_seconds', 0):g}s | XP {row.get('xp_earned', 0)}"
            )
    lines.extend(["", "Practice data is a learning aid, not a hiring or diagnostic assessment."])

    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=88, break_long_words=True) or [""])
    page_lines = [wrapped[i:i + 46] for i in range(0, len(wrapped), 46)] or [["ShadowIntelX IQ - Performance Intelligence"]]

    page_ids = [4 + 2 * i for i in range(len(page_lines))]
    content_ids = [page_id + 1 for page_id in page_ids]
    objects: list[bytes] = [b""] * (3 + len(page_ids) * 2)
    objects[0] = f"<< /Type /Catalog /Pages 2 0 R >>".encode("ascii")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    objects[2] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    for page_id, content_id, content_lines in zip(page_ids, content_ids, page_lines):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        stream = _make_content(content_lines)
        objects[content_id - 1] = f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream"

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
