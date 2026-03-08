"""
GraceFinance — CSV Export Routes
File: app/routers/export.py

Endpoints:
  GET /api/export/checkins    → download check-in history as CSV (Pro+)
  GET /api/export/fcs-trend   → download FCS metric snapshots as CSV (Pro+)

Tier gating: Free users receive HTTP 403 with upgrade prompt.
"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.database import get_db
from app.services.auth import get_current_user
from app.services.tier_gate import require_feature
from app.models import User
from app.models.checkin import CheckInResponse, UserMetricSnapshot

router = APIRouter(prefix="/api/export", tags=["export"])


def _build_csv(headers: list[str], rows: list[list]) -> str:
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
# 1. Export Check-In History (Pro+)
# ──────────────────────────────────────────────
@router.get("/checkins")
def export_checkin_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ── Tier gate: Pro+ only ──
    require_feature(current_user, "data_export_csv")

    checkins = (
        db.query(CheckInResponse)
        .filter(CheckInResponse.user_id == current_user.id)
        .order_by(asc(CheckInResponse.checkin_date))
        .all()
    )

    headers = [
        "checkin_date",
        "question_id",
        "question_text",
        "answer_value",
        "dimension",
    ]

    rows = []
    for c in checkins:
        rows.append([
            c.checkin_date.strftime("%Y-%m-%d %H:%M:%S") if c.checkin_date else "",
            getattr(c, "question_id", ""),
            getattr(c, "question_text", ""),
            getattr(c, "answer_value", getattr(c, "response", "")),
            getattr(c, "dimension", ""),
        ])

    filename = f"gracefinance_checkins_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return _csv_response(_build_csv(headers, rows), filename)


# ──────────────────────────────────────────────
# 2. Export FCS Trend Data (Pro+)
# ──────────────────────────────────────────────
@router.get("/fcs-trend")
def export_fcs_trend(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ── Tier gate: Pro+ only ──
    require_feature(current_user, "data_export_csv")

    snapshots = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.user_id == current_user.id)
        .order_by(asc(UserMetricSnapshot.computed_at))
        .all()
    )

    headers = [
        "date",
        "fcs_composite",
        "current_stability",
        "future_outlook",
        "purchasing_power",
        "emergency_readiness",
        "financial_agency",
        "bsi_score",
        "checkin_count",
    ]

    rows = []
    for s in snapshots:
        rows.append([
            s.computed_at.strftime("%Y-%m-%d %H:%M:%S") if s.computed_at else "",
            s.fcs_composite or "",
            s.current_stability or "",
            s.future_outlook or "",
            s.purchasing_power or "",
            s.emergency_readiness or "",
            s.financial_agency or "",
            s.bsi_score or "",
            s.checkin_count or 0,
        ])

    filename = f"gracefinance_fcs_trend_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return _csv_response(_build_csv(headers, rows), filename)