"""
GraceFinance — CSV Export Routes
File: app/routers/export.py

Endpoints:
  GET /api/export/checkins    -> download check-in history as CSV (Pro+)
  GET /api/export/fcs-trend   -> download FCS metric snapshots as CSV (Pro+)

Tier gating: Free users receive HTTP 403 with upgrade prompt.

v2 FIX: Corrected model import path and matched actual column names
        from CheckInResponse / UserMetricSnapshot models.
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
from app.models.models import User
from app.models.checkin import CheckInResponse, UserMetricSnapshot

router = APIRouter(prefix="/api/export", tags=["export"])


def _build_csv(headers, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    content = buf.getvalue()
    buf.close()
    return content


def _csv_response(content, filename):
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="' + filename + '"'},
    )


# ──────────────────────────────────────────────
# 1. Export Check-In History (Pro+)
# ──────────────────────────────────────────────
@router.get("/checkins")
def export_checkin_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
        "dimension",
        "raw_value",
        "scale_max",
        "normalized_value",
    ]

    rows = []
    for c in checkins:
        rows.append([
            c.checkin_date.strftime("%Y-%m-%d %H:%M:%S") if c.checkin_date else "",
            c.question_id or "",
            c.dimension or "",
            c.raw_value if c.raw_value is not None else "",
            c.scale_max if c.scale_max is not None else "",
            round(c.normalized_value, 4) if c.normalized_value is not None else "",
        ])

    filename = "gracefinance_checkins_" + datetime.utcnow().strftime("%Y%m%d") + ".csv"
    return _csv_response(_build_csv(headers, rows), filename)


# ──────────────────────────────────────────────
# 2. Export FCS Trend Data (Pro+)
# ──────────────────────────────────────────────
@router.get("/fcs-trend")
def export_fcs_trend(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
        "fcs_raw",
        "fcs_behavior",
        "fcs_consistency",
        "fcs_trend",
        "fcs_confidence",
        "current_stability",
        "future_outlook",
        "purchasing_power",
        "emergency_readiness",
        "financial_agency",
        "bsi_score",
        "bsi_shock",
        "checkin_count",
        "fcs_slope_7d",
        "fcs_slope_30d",
    ]

    rows = []
    for s in snapshots:
        rows.append([
            s.computed_at.strftime("%Y-%m-%d %H:%M:%S") if s.computed_at else "",
            round(s.fcs_composite, 4) if s.fcs_composite is not None else "",
            round(s.fcs_raw, 4) if s.fcs_raw is not None else "",
            round(s.fcs_behavior, 4) if s.fcs_behavior is not None else "",
            round(s.fcs_consistency, 4) if s.fcs_consistency is not None else "",
            round(s.fcs_trend, 4) if s.fcs_trend is not None else "",
            round(s.fcs_confidence, 4) if s.fcs_confidence is not None else "",
            round(s.current_stability, 4) if s.current_stability is not None else "",
            round(s.future_outlook, 4) if s.future_outlook is not None else "",
            round(s.purchasing_power, 4) if s.purchasing_power is not None else "",
            round(s.emergency_readiness, 4) if s.emergency_readiness is not None else "",
            round(s.financial_agency, 4) if s.financial_agency is not None else "",
            round(s.bsi_score, 4) if s.bsi_score is not None else "",
            s.bsi_shock,
            s.checkin_count or 0,
            round(s.fcs_slope_7d, 6) if s.fcs_slope_7d is not None else "",
            round(s.fcs_slope_30d, 6) if s.fcs_slope_30d is not None else "",
        ])

    filename = "gracefinance_fcs_trend_" + datetime.utcnow().strftime("%Y%m%d") + ".csv"
    return _csv_response(_build_csv(headers, rows), filename)