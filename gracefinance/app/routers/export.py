"""
GraceFinance — CSV Export Routes
File: app/routers/export.py

Endpoints:
  GET /api/export/checkins    → download check-in history as CSV
  GET /api/export/fcs-trend   → download FCS / metric snapshots as CSV

NOTE: Adjust the column names inside the writer loops if your
      CheckInResponse or UserMetricSnapshot fields differ from
      what's assumed below. Grep your checkin.py to confirm.
"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user  # adjust if your dep lives elsewhere
from app.models import User
from app.models.checkin import CheckInResponse, UserMetricSnapshot  # both live here per your note

router = APIRouter(prefix="/api/export", tags=["export"])


def _build_csv(rows: list[list], headers: list[str]) -> str:
    """Write headers + rows to an in-memory CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    content = buf.getvalue()
    buf.close()
    return content


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────────────────────────────
# 1. Export Check-In History
# ──────────────────────────────────────────────
@router.get("/checkins")
def export_checkin_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    checkins = (
        db.query(CheckInResponse)
        .filter(CheckInResponse.user_id == current_user.id)
        .order_by(CheckInResponse.created_at.asc())
        .all()
    )

    # ─── Adjust these attribute names to match your CheckInResponse columns ───
    # Common patterns: question_id, question_text, answer/response, score, category, dimension
    headers = [
        "date",
        "question_id",
        "question_text",
        "response",
        "score",
        "dimension",
    ]

    rows = []
    for c in checkins:
        rows.append([
            c.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(c, "created_at", None) else "",
            getattr(c, "question_id", ""),
            getattr(c, "question_text", ""),
            getattr(c, "response", getattr(c, "answer", "")),
            getattr(c, "score", ""),
            getattr(c, "dimension", getattr(c, "category", "")),
        ])

    filename = f"gracefinance_checkins_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return _csv_response(_build_csv(rows, headers), filename)


# ──────────────────────────────────────────────
# 2. Export FCS Trend Data
# ──────────────────────────────────────────────
@router.get("/fcs-trend")
def export_fcs_trend(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snapshots = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.user_id == current_user.id)
        .order_by(UserMetricSnapshot.created_at.asc())
        .all()
    )

    # ─── Adjust these to your actual UserMetricSnapshot columns ───
    # Your 5 FCS dimensions + composite + BSI
    headers = [
        "date",
        "fcs_composite",
        "spending_awareness",
        "saving_habits",
        "debt_management",
        "income_stability",
        "financial_planning",
        "bsi",
    ]

    rows = []
    for s in snapshots:
        rows.append([
            s.created_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(s, "created_at", None) else "",
            getattr(s, "fcs_composite", getattr(s, "composite_score", "")),
            getattr(s, "spending_awareness", ""),
            getattr(s, "saving_habits", ""),
            getattr(s, "debt_management", ""),
            getattr(s, "income_stability", ""),
            getattr(s, "financial_planning", ""),
            getattr(s, "bsi", ""),
        ])

    filename = f"gracefinance_fcs_trend_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return _csv_response(_build_csv(rows, headers), filename)