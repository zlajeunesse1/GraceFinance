"""
Daily Engagement Emails — GraceFinance
═══════════════════════════════════════
v1.1 — Fixes:
  - HTML-escapes user names to prevent injection
  - Added email preferences link (unsubscribe path)

Sends a rotating motivational email to all verified users every morning.
"""

import smtplib
import logging
from html import escape as html_escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ══════════════════════════════════════════
#  POSITIVE SIGN-OFF (rotates with message)
# ══════════════════════════════════════════

POSITIVE_CLOSINGS = [
    "We're rooting for you. Always.",
    "You're doing better than you think.",
    "Proud of you for showing up today.",
    "Your consistency is your superpower.",
    "We believe in your journey.",
    "One step at a time. You've got this.",
    "The GraceFinance community is behind you.",
    "Keep going. You're building something real.",
    "Today matters. And so do you.",
    "Your future is brighter than you realize.",
]

# ══════════════════════════════════════════
#  ROTATING DAILY MESSAGES (30 messages = full month rotation)
# ══════════════════════════════════════════

DAILY_MESSAGES = [
    {"subject": "Your finances deserve 2 minutes today", "body": "The most powerful financial habit isn't budgeting. It's awareness. Take 2 minutes to check in with yourself today. How confident do you feel about your money right now?\n\nYour daily check-in is waiting."},
    {"subject": "Small wins compound, just like interest", "body": "Every time you check in, you're building something most people never develop: real financial self-awareness. That compounds over time, just like the money you're learning to manage better.\n\nKeep your streak alive today."},
    {"subject": "Debt doesn't define you. Your next move does.", "body": "If you're carrying debt, you're not alone, and you're not stuck. The fact that you're tracking your financial confidence means you're already doing more than most.\n\nOne payment at a time. One check-in at a time. That's how it's done."},
    {"subject": "What's one financial win you can get today?", "body": "It doesn't have to be big. Skip the impulse buy. Move $5 to savings. Check your bank balance. Review a subscription.\n\nSmall moves, repeated daily, change everything. Start with your check-in."},
    {"subject": "Your FCS is more than a number", "body": "Your Financial Confidence Score isn't about being perfect. It's about being honest with yourself. Every check-in gives you a clearer picture of where you stand and where you're heading.\n\nCheck in today and watch your trend build."},
    {"subject": "The 5-minute habit that builds wealth", "body": "Most people spend more time choosing what to watch on TV than reviewing their finances. You're different. You show up.\n\n5 minutes of awareness today can save you hours of stress later. Your check-in is ready."},
    {"subject": "Consistency beats intensity, every time", "body": "You don't need a perfect budget. You don't need a six-figure salary. What you need is consistency. Showing up, checking in, staying aware.\n\nThat's what separates people who build confidence from people who just worry about money."},
    {"subject": "Your future self will thank you", "body": "Every check-in you complete is a data point. Every data point tells a story. And that story, your story, is one of someone who chose to pay attention when it mattered.\n\nDon't break the chain. Check in today."},
    {"subject": "Money stress is real. So is your progress.", "body": "If money's been weighing on you, that's normal. But here's what's different now: you're measuring it. You're tracking it. You're not running from it.\n\nThat alone puts you ahead. Keep going."},
    {"subject": "One check-in. Five dimensions. Total clarity.", "body": "Stability. Outlook. Purchasing Power. Emergency Readiness. Financial Agency. Each check-in gives you a read across all five. No guesswork, just honest signal.\n\nYour daily check-in takes less than a minute."},
    {"subject": "The best time to start was yesterday. The next best time is now.", "body": "Whether you're paying off debt, building savings, or just trying to feel less stressed about money, the path forward starts with awareness.\n\nCheck in today. Grace is here to help."},
    {"subject": "You're building something most people never will", "body": "Financial confidence isn't taught in school. It's built through daily practice, through checking in, staying aware, and making slightly better decisions over time.\n\nYou're doing that. Don't stop now."},
    {"subject": "Autopay your bills. Manual-pay your attention.", "body": "Automate the boring stuff. But never automate your awareness. The few minutes you spend checking in are the most valuable minutes in your financial day.\n\nYour check-in is waiting."},
    {"subject": "Every streak starts with day one", "body": "If you missed yesterday, that's okay. Today is a fresh start. The only check-in that matters is the next one.\n\nShow up today. That's all it takes."},
    {"subject": "Your money habits are changing. Can you feel it?", "body": "Most people don't notice their own growth. But your FCS does. It's tracking every shift in how you think, feel, and act around money.\n\nCheck in today and see where you stand."},
    {"subject": "What would 1% better look like today?", "body": "You don't need a financial overhaul. You need 1% better. One fewer impulse buy. One more minute reviewing your accounts. One check-in to stay on track.\n\nThat 1% adds up fast."},
    {"subject": "Grace tip: review one subscription this week", "body": "The average person spends $200+/month on subscriptions they barely use. Take 60 seconds this week to review just one. Cancel it, downgrade it, or keep it, but make it a conscious choice.\n\nStart with your check-in today."},
    {"subject": "Confidence isn't the absence of problems", "body": "Financial confidence doesn't mean everything is perfect. It means you know where you stand, you have a direction, and you're showing up consistently.\n\nThat's exactly what you're building. Keep it going."},
    {"subject": "Your streak is a signal. Don't ignore it.", "body": "A growing streak means you're building discipline. A broken streak means you're human. Either way, the next check-in is what matters most.\n\nLet's go."},
    {"subject": "The GraceFinance Index needs you", "body": "Every check-in you complete helps power the GraceFinance Composite Index, a real-time measure of financial confidence across our entire community.\n\nYour data matters. Your voice matters. Check in today."},
    {"subject": "Debt payoff isn't linear, and that's okay", "body": "Some months you'll crush it. Some months you'll barely make minimums. What matters is that you don't lose sight of the direction.\n\nYour FCS tracks the trend, not just the moment. Check in today."},
    {"subject": "Morning routine: coffee, check-in, clarity", "body": "Add your GraceFinance check-in to your morning routine. It takes less than a minute and sets the tone for how you think about money all day.\n\nYour questions are ready."},
    {"subject": "You're in the top 1% of financial awareness", "body": "Most people have no idea where they stand financially. No score. No trend. No direction. You do.\n\nThat's not a small thing. That's everything. Keep checking in."},
    {"subject": "Grace tip: set one 90-day money goal", "body": "People who write down financial goals are significantly more likely to achieve them. Pick one thing, pay off a card, save $500, build a 2-week buffer, and commit to 90 days.\n\nGrace can help you track it. Start with today's check-in."},
    {"subject": "The hardest part is already behind you", "body": "You signed up. You started checking in. You chose to pay attention to your finances when most people look away.\n\nThe hardest part, starting, is done. Now it's just momentum."},
    {"subject": "Emergency fund check: could you handle $500 today?", "body": "If a $500 surprise expense would stress you out, you're not alone. But knowing that, and tracking it, is exactly how you change it.\n\nYour check-in measures your emergency readiness. Let's see where you are today."},
    {"subject": "Your financial agency score matters more than you think", "body": "Financial agency is about whether you're actively managing your money or just letting it happen to you. It's the one dimension you can improve immediately, just by paying attention.\n\nCheck in today."},
    {"subject": "Don't just earn more. Understand more.", "body": "Income helps. But understanding your relationship with money? That's what GraceFinance measures. And it's what actually changes your outcomes long-term.\n\nYour daily check-in is ready."},
    {"subject": "Payday isn't a plan. Check-ins are.", "body": "Waiting for the next paycheck isn't a financial strategy. Tracking your confidence, your habits, and your direction? That is.\n\nCheck in today. Build the data that builds your future."},
    {"subject": "30 seconds. 5 questions. Real clarity.", "body": "That's all it takes. Your daily check-in is designed to be fast, honest, and meaningful. No spreadsheets. No guilt. Just a clear read on where you stand.\n\nLet's go."},
]


# ══════════════════════════════════════════
#  EMAIL BUILDER
# ══════════════════════════════════════════

def _build_email(to_email: str, first_name: str, subject: str, body: str, closing: str) -> MIMEMultipart:
    """Build a clean, branded daily email with HTML-escaped name and unsubscribe link."""
    # FIX: HTML-escape user name
    safe_name = html_escape(first_name) if first_name else "there"
    greeting = f"Hey {safe_name},"

    html = f"""
    <div style="font-family: -apple-system, 'Segoe UI', sans-serif; max-width: 520px; margin: 0 auto; padding: 32px 24px; color: #1a1a1a;">
        <div style="margin-bottom: 24px;">
            <span style="font-size: 14px; font-weight: 700; letter-spacing: -0.02em;">GraceFinance</span>
        </div>

        <p style="font-size: 15px; line-height: 1.7; margin: 0 0 16px;">{greeting}</p>
        <p style="font-size: 15px; line-height: 1.7; margin: 0 0 24px; white-space: pre-line;">{body}</p>

        <a href="https://gracefinance.co/dashboard"
           style="display: inline-block; padding: 12px 28px; background: #000; color: #fff;
                  text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 600;">
            Open GraceFinance
        </a>

        <p style="font-size: 14px; line-height: 1.6; margin: 28px 0 0; color: #374151; font-style: italic;">
            {closing}
        </p>
        <p style="font-size: 13px; color: #374151; margin: 4px 0 0; font-weight: 600;">
            - The GraceFinance Team
        </p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 28px 0 16px;" />
        <p style="font-size: 11px; color: #999; margin: 0;">
            GraceFinance - Where Financial Confidence Is Measured.<br>
            You're receiving this because you have a GraceFinance account.<br>
            <a href="https://gracefinance.co/settings" style="color: #999; text-decoration: underline;">Email preferences</a>
        </p>
    </div>
    """

    plain_text = f"{greeting}\n\n{body}\n\nOpen GraceFinance: https://gracefinance.co/dashboard\n\n{closing}\n- The GraceFinance Team\n\nGraceFinance - Where Financial Confidence Is Measured.\nEmail preferences: https://gracefinance.co/settings"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"GraceFinance <{settings.smtp_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


# ══════════════════════════════════════════
#  SEND TO ALL USERS
# ══════════════════════════════════════════

def send_daily_engagement_emails():
    """
    Send today's rotating motivational email to all verified users.
    Called by APScheduler every morning at 8am EST.
    """
    db: Session = SessionLocal()
    try:
        day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
        message = DAILY_MESSAGES[day_of_year % len(DAILY_MESSAGES)]
        closing = POSITIVE_CLOSINGS[day_of_year % len(POSITIVE_CLOSINGS)]

        users = db.query(User).filter(User.email_verified == True).all()

        if not users:
            logger.info("No verified users to email.")
            return

        sent = 0
        failed = 0

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)

            for user in users:
                try:
                    email = _build_email(
                        to_email=user.email,
                        first_name=user.first_name or "",
                        subject=message["subject"],
                        body=message["body"],
                        closing=closing,
                    )
                    server.sendmail(settings.smtp_user, user.email, email.as_string())
                    sent += 1
                except Exception as e:
                    logger.error(f"Failed to send to {user.email}: {e}")
                    failed += 1

        logger.info(f"Daily emails sent: {sent} success, {failed} failed, {len(users)} total users")

    except Exception as e:
        logger.error(f"Daily email job failed: {e}")
    finally:
        db.close()