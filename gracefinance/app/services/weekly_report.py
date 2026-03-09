"""
Weekly Report Service — Personalized + Index Digest
════════════════════════════════════════════════════
v1.1 — Fixes:
  - API key loaded from config, not os.getenv
  - checkins_this_week counts distinct days, not response rows
  - HTML-escapes user names in email templates

Runs every Sunday at 6:00 PM ET (23:00 UTC).
"""

import smtplib
import logging
from html import escape as html_escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func, distinct, cast, Date

from app.database import SessionLocal
from app.models import User
from app.models.checkin import UserMetricSnapshot, CheckInResponse, DailyIndex
from app.services.bsi_engine import get_latest_bsi, compute_population_bsi
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

EASTERN = ZoneInfo("America/New_York")

FROM_EMAIL = settings.smtp_user
FROM_NAME = "GraceFinance"


# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY — called by APScheduler every Sunday 23:00 UTC
# ═══════════════════════════════════════════════════════════════

def send_weekly_reports():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.email_verified == True).all()

        if not users:
            logger.info("No verified users for weekly reports.")
            return

        index_report = _build_index_report(db)

        sent = 0
        failed = 0

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)

            for user in users:
                try:
                    tier = str(getattr(user, "subscription_tier", "free") or "free").lower()
                    personal = _build_personal_report(db, user, tier)

                    grace_insight = None
                    if tier == "premium":
                        grace_insight = _generate_grace_weekly_insight(db, user, personal)

                    html = _render_email(user, tier, index_report, personal, grace_insight)
                    plain = _render_plain(user, personal, index_report)

                    date_str = datetime.now(EASTERN).strftime("%b %d")
                    subject = f"Your Weekly Financial Confidence Report — {date_str}"

                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = subject
                    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
                    msg["To"] = user.email
                    msg.attach(MIMEText(plain, "plain"))
                    msg.attach(MIMEText(html, "html"))

                    server.sendmail(FROM_EMAIL, user.email, msg.as_string())
                    sent += 1

                except Exception as e:
                    logger.error(f"Weekly report failed for {user.email}: {e}")
                    failed += 1

        logger.info(f"Weekly reports: {sent} sent, {failed} failed, {len(users)} total")

    except Exception as e:
        logger.error(f"Weekly report job failed: {e}")
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
#  INDEX REPORT (same for all users)
# ═══════════════════════════════════════════════════════════════

def _build_index_report(db: Session) -> Dict:
    latest = (
        db.query(DailyIndex)
        .filter(DailyIndex.segment == "national")
        .order_by(desc(DailyIndex.computed_at))
        .first()
    )

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    prev = (
        db.query(DailyIndex)
        .filter(and_(DailyIndex.segment == "national", DailyIndex.computed_at <= week_ago))
        .order_by(desc(DailyIndex.computed_at))
        .first()
    )

    # Active contributors in last 14 days
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    contributors = (
        db.query(func.count(distinct(CheckInResponse.user_id)))
        .filter(CheckInResponse.checkin_date >= stale_cutoff)
        .scalar() or 0
    )

    pop_bsi = compute_population_bsi(db)

    gfci = latest.gf_rwi_composite if latest else None
    gfci_prev = prev.gf_rwi_composite if prev else None
    gfci_delta = round(gfci - gfci_prev, 2) if gfci and gfci_prev else None

    return {
        "gfci": gfci,
        "gfci_delta": gfci_delta,
        "contributors": contributors,
        "user_count": latest.user_count if latest else 0,
        "population_bsi": pop_bsi.get("population_bsi"),
        "population_bsi_delta": pop_bsi.get("population_delta"),
        "top_patterns": pop_bsi.get("patterns", {}),
        "index_date": latest.index_date.isoformat() if latest else None,
    }


# ═══════════════════════════════════════════════════════════════
#  PERSONAL REPORT (tier-gated depth)
# ═══════════════════════════════════════════════════════════════

def _build_personal_report(db: Session, user: User, tier: str) -> Dict:
    latest = (
        db.query(UserMetricSnapshot)
        .filter(UserMetricSnapshot.user_id == user.id)
        .order_by(desc(UserMetricSnapshot.computed_at))
        .first()
    )

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    previous = (
        db.query(UserMetricSnapshot)
        .filter(and_(UserMetricSnapshot.user_id == user.id, UserMetricSnapshot.computed_at <= week_ago))
        .order_by(desc(UserMetricSnapshot.computed_at))
        .first()
    )

    # FIX: Count distinct check-in DAYS, not response rows
    week_start = datetime.now(timezone.utc) - timedelta(days=7)
    checkins = (
        db.query(func.count(func.distinct(cast(CheckInResponse.checkin_date, Date))))
        .filter(and_(CheckInResponse.user_id == user.id, CheckInResponse.checkin_date >= week_start))
        .scalar() or 0
    )

    fcs = float(latest.fcs_composite) if latest and latest.fcs_composite else None
    fcs_prev = float(previous.fcs_composite) if previous and previous.fcs_composite else None
    fcs_delta = round(fcs - fcs_prev, 2) if fcs and fcs_prev else None

    report = {
        "first_name": user.first_name or "there",
        "fcs": fcs,
        "fcs_delta": fcs_delta,
        "fcs_band": _score_band(fcs) if fcs else None,
        "streak": getattr(user, "current_streak", 0) or 0,
        "checkins_this_week": checkins,
        "tier": tier,
    }

    # Pro+ gets dimensions
    if tier in ("pro", "premium") and latest:
        dim_labels = {
            "current_stability": "Stability",
            "future_outlook": "Outlook",
            "purchasing_power": "Purchasing Power",
            "emergency_readiness": "Emergency Readiness",
            "financial_agency": "Financial Agency",
        }
        dims = {}
        for field, label in dim_labels.items():
            cur = getattr(latest, field, None)
            prev_val = getattr(previous, field, None) if previous else None
            if cur is not None:
                score = round(float(cur) * 100, 1)
                delta = round((float(cur) - float(prev_val)) * 100, 1) if prev_val is not None else None
                dims[field] = {"label": label, "score": score, "delta": delta}

        report["dimensions"] = dims

        if dims:
            movers = [(k, abs(v["delta"])) for k, v in dims.items() if v.get("delta")]
            if movers:
                biggest = max(movers, key=lambda x: x[1])
                report["biggest_mover"] = {**dims[biggest[0]], "field": biggest[0]}

    # Pro+ gets BSI
    if tier in ("pro", "premium"):
        bsi = get_latest_bsi(db, user.id)
        if bsi:
            report["bsi"] = {
                "composite": bsi.bsi_composite,
                "delta": bsi.bsi_delta,
                "stress_patterns": bsi.stress_patterns or [],
                "positive_patterns": bsi.positive_patterns or [],
                "coaching_reflections": bsi.coaching_reflections or [],
                "dimension_impacts": bsi.dimension_impacts or {},
            }

    return report


# ═══════════════════════════════════════════════════════════════
#  GRACE AI WEEKLY INSIGHT (Premium only)
# ═══════════════════════════════════════════════════════════════

def _generate_grace_weekly_insight(db: Session, user: User, report: Dict) -> Optional[str]:
    # FIX: Use config for API key, not os.getenv
    api_key = settings.anthropic_api_key
    if not api_key:
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        parts = [f"User: {report.get('first_name', 'User')}"]

        if report.get("fcs"):
            parts.append(f"FCS: {report['fcs']} ({report.get('fcs_band', '')})")
        if report.get("fcs_delta"):
            d = "improved" if report["fcs_delta"] > 0 else "declined"
            parts.append(f"FCS {d} by {abs(report['fcs_delta'])} pts this week")
        if report.get("streak"):
            parts.append(f"Streak: {report['streak']} days")
        if report.get("checkins_this_week"):
            parts.append(f"Check-ins this week: {report['checkins_this_week']}")
        if report.get("biggest_mover"):
            m = report["biggest_mover"]
            parts.append(f"Biggest move: {m['label']} ({'+' if m.get('delta', 0) > 0 else ''}{m.get('delta', 0):.1f} pts)")

        if report.get("bsi"):
            bsi = report["bsi"]
            parts.append(f"BSI: {bsi['composite']}")
            if bsi.get("stress_patterns"):
                names = [p["label"] for p in bsi["stress_patterns"]]
                parts.append(f"Stress patterns: {', '.join(names)}")
            if bsi.get("coaching_reflections"):
                for r in bsi["coaching_reflections"][:2]:
                    parts.append(f"Reflection: {r.get('reflection', '')}")

        context = "\n".join(parts)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=(
                "You are Grace, the GraceFinance AI financial coach. "
                "Write a brief personalized weekly insight for this user's email report. "
                "2-3 sentences max. Be warm, specific to their data, actionable. "
                "Reference their actual numbers naturally. End with one specific thing to focus on next week. "
                "Do NOT include greetings, sign-offs, or disclaimers."
            ),
            messages=[{"role": "user", "content": f"Write a weekly insight:\n{context}"}],
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Grace weekly insight failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
#  EMAIL RENDERING — HTML
# ═══════════════════════════════════════════════════════════════

def _render_email(user, tier, index_report, personal, grace_insight=None) -> str:
    # FIX: HTML-escape user name
    name = html_escape(user.first_name or "there")
    fcs = personal.get("fcs")
    fcs_delta = personal.get("fcs_delta")
    fcs_band = personal.get("fcs_band", "")
    streak = personal.get("streak", 0)
    checkins = personal.get("checkins_this_week", 0)

    fcs_delta_html = ""
    if fcs_delta is not None:
        arrow = "↑" if fcs_delta > 0 else "↓" if fcs_delta < 0 else "→"
        color = "#10b981" if fcs_delta > 0 else "#ef4444" if fcs_delta < 0 else "#666"
        fcs_delta_html = f'<span style="color:{color};font-weight:600">{arrow} {abs(fcs_delta):.1f}</span>'

    gfci = index_report.get("gfci")
    contributors = index_report.get("contributors", 0)
    gfci_delta = index_report.get("gfci_delta")
    gfci_delta_html = ""
    if gfci_delta is not None:
        arrow = "↑" if gfci_delta > 0 else "↓" if gfci_delta < 0 else "→"
        color = "#10b981" if gfci_delta > 0 else "#ef4444" if gfci_delta < 0 else "#666"
        gfci_delta_html = f'<span style="color:{color}">{arrow} {abs(gfci_delta):.1f}</span>'

    dims_html = ""
    if tier in ("pro", "premium") and personal.get("dimensions"):
        rows = ""
        for field, dim in personal["dimensions"].items():
            d_html = ""
            if dim.get("delta") is not None:
                a = "↑" if dim["delta"] > 0 else "↓" if dim["delta"] < 0 else "→"
                c = "#10b981" if dim["delta"] > 0 else "#ef4444" if dim["delta"] < 0 else "#666"
                d_html = f'<span style="color:{c};font-size:12px">{a} {abs(dim["delta"]):.1f}</span>'
            rows += f'<tr><td style="padding:8px 0;color:#ccc;font-size:13px">{dim["label"]}</td><td style="padding:8px 0;text-align:right;color:#fff;font-weight:600;font-size:14px">{dim["score"]:.0f}</td><td style="padding:8px 0;text-align:right;width:60px">{d_html}</td></tr>'

        dims_html = f'''
        <div style="margin:24px 0;padding:20px;background:#111;border:1px solid #222;border-radius:10px">
            <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Your Dimensions</div>
            <table style="width:100%;border-collapse:collapse">{rows}</table>
        </div>'''

    bsi_html = ""
    if tier in ("pro", "premium") and personal.get("bsi"):
        bsi = personal["bsi"]
        bsi_color = "#10b981" if bsi["composite"] > 20 else "#ef4444" if bsi["composite"] < -20 else "#888"

        patterns_html = ""
        for p in (bsi.get("stress_patterns") or []):
            patterns_html += f'<div style="color:#ef4444;font-size:12px;margin:4px 0">⚠ {html_escape(str(p.get("label", "")))}</div>'
        for p in (bsi.get("positive_patterns") or []):
            patterns_html += f'<div style="color:#10b981;font-size:12px;margin:4px 0">✓ {html_escape(str(p.get("label", "")))}</div>'

        reflections_html = ""
        for r in (bsi.get("coaching_reflections") or [])[:2]:
            reflections_html += f'<p style="color:#999;font-size:12px;line-height:1.6;margin:8px 0 0;font-style:italic">{html_escape(str(r.get("reflection", "")))}</p>'

        bsi_html = f'''
        <div style="margin:24px 0;padding:20px;background:#111;border:1px solid #222;border-radius:10px">
            <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Behavioral Shift Indicator</div>
            <div style="font-size:28px;font-weight:700;color:{bsi_color};margin-bottom:8px">{bsi["composite"]:.0f}</div>
            {patterns_html}
            {reflections_html}
        </div>'''

    grace_html = ""
    if grace_insight:
        grace_html = f'''
        <div style="margin:24px 0;padding:20px;background:#0a1a0f;border:1px solid #1a3a1f;border-radius:10px">
            <div style="margin-bottom:12px">
                <span style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em">Grace's Weekly Insight</span>
            </div>
            <p style="color:#ccc;font-size:14px;line-height:1.7;margin:0">{html_escape(grace_insight)}</p>
        </div>'''

    upgrade_html = ""
    if tier == "free":
        upgrade_html = '''
        <div style="margin:24px 0;padding:20px;background:#111;border:1px solid #222;border-radius:10px;text-align:center">
            <div style="font-size:13px;color:#ccc;margin-bottom:12px">Want the full breakdown? Dimensions, BSI patterns, and AI insights.</div>
            <a href="https://gracefinance.co/upgrade" style="display:inline-block;padding:10px 24px;background:#fff;color:#000;border-radius:7px;font-size:13px;font-weight:700;text-decoration:none">See Plans</a>
        </div>'''

    date_str = datetime.now(EASTERN).strftime("%B %d, %Y")

    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#000;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
    <div style="max-width:560px;margin:0 auto;padding:32px 20px">
        <div style="margin-bottom:32px">
            <span style="font-size:14px;font-weight:600;color:#fff;letter-spacing:-0.02em">GraceFinance</span>
        </div>

        <h1 style="font-size:22px;font-weight:300;color:#fff;margin:0 0 4px;letter-spacing:-0.02em">Weekly Report</h1>
        <p style="font-size:12px;color:#666;margin:0 0 28px">{date_str}</p>
        <p style="font-size:14px;color:#999;margin:0 0 24px;line-height:1.6">Hey {name}, here's how your financial confidence shaped up this week.</p>

        <div style="padding:24px;background:#111;border:1px solid #222;border-radius:10px;text-align:center;margin-bottom:16px">
            <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Your Financial Confidence Score</div>
            <div style="font-size:42px;font-weight:700;color:#fff;letter-spacing:-0.03em">{f'{fcs:.1f}' if fcs else '—'}</div>
            <div style="font-size:12px;color:#888;margin-top:4px">{fcs_band} {fcs_delta_html}</div>
            <div style="margin-top:16px">
                <span style="font-size:16px;font-weight:600;color:#fff">{streak}d</span>
                <span style="font-size:10px;color:#666;text-transform:uppercase;margin:0 16px 0 4px">streak</span>
                <span style="font-size:16px;font-weight:600;color:#fff">{checkins}</span>
                <span style="font-size:10px;color:#666;text-transform:uppercase;margin-left:4px">check-ins</span>
            </div>
        </div>

        {dims_html}
        {bsi_html}
        {grace_html}
        {upgrade_html}

        <div style="margin:28px 0;padding:20px;background:#111;border:1px solid #222;border-radius:10px">
            <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">GraceFinance Index</div>
            <div style="font-size:28px;font-weight:700;color:#fff;display:inline">{f'{gfci:.1f}' if gfci else '—'}</div>
            <span style="font-size:12px;color:#666;margin-left:8px">{gfci_delta_html} this week</span>
            <div style="font-size:12px;color:#666;margin-top:8px">{contributors} contributors</div>
        </div>

        <div style="text-align:center;margin:28px 0">
            <a href="https://gracefinance.co/dashboard" style="display:inline-block;padding:12px 28px;background:#fff;color:#000;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none">Open Dashboard</a>
        </div>

        <hr style="border:none;border-top:1px solid #1a1a1a;margin:28px 0 20px">
        <p style="font-size:11px;color:#444;text-align:center;margin:0">
            GraceFinance · Where Financial Confidence Is Measured.<br>
            <a href="https://gracefinance.co" style="color:#555;text-decoration:none">gracefinance.co</a><br>
            <a href="https://gracefinance.co/settings" style="color:#444;text-decoration:none;font-size:10px">Email preferences</a>
        </p>
    </div>
</body>
</html>'''


# ═══════════════════════════════════════════════════════════════
#  PLAIN TEXT FALLBACK
# ═══════════════════════════════════════════════════════════════

def _render_plain(user, personal, index_report) -> str:
    name = user.first_name or "there"
    fcs = personal.get("fcs")
    fcs_delta = personal.get("fcs_delta")
    streak = personal.get("streak", 0)
    checkins = personal.get("checkins_this_week", 0)
    gfci = index_report.get("gfci")

    lines = [
        f"Hey {name},",
        "",
        "Here's your weekly financial confidence report.",
        "",
        f"FCS: {f'{fcs:.1f}' if fcs else 'No data yet'} ({personal.get('fcs_band', '')})",
    ]

    if fcs_delta is not None:
        direction = "up" if fcs_delta > 0 else "down"
        lines.append(f"  {direction} {abs(fcs_delta):.1f} points this week")

    lines.extend([
        f"Streak: {streak} days",
        f"Check-ins this week: {checkins}",
        "",
        f"GraceFinance Index: {f'{gfci:.1f}' if gfci else 'N/A'}",
        f"Contributors: {index_report.get('contributors', 0)}",
        "",
        "Open your dashboard: https://gracefinance.co/dashboard",
        "",
        "Manage email preferences: https://gracefinance.co/settings",
        "",
        "GraceFinance — Where Financial Confidence Is Measured.",
    ])

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _score_band(score: float) -> str:
    if score >= 80: return "Thriving"
    elif score >= 65: return "Strong"
    elif score >= 50: return "Building"
    elif score >= 35: return "Growing"
    elif score >= 20: return "Emerging"
    return "Starting"