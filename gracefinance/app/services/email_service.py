"""
GraceFinance — Email Service
Sends transactional emails via Google SMTP (support@gracefinance.co).

Requires Railway env vars:
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=support@gracefinance.co
  SMTP_PASSWORD=<16-char app password>
  FRONTEND_URL=https://gracefinance.co
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _send(to: str, subject: str, html: str, text: str):
    """Core SMTP send. Logs error and returns False on failure — never crashes signup."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"GraceFinance <{settings.smtp_user}>"
        msg["To"] = to
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, to, msg.as_string())

        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


def send_verification_email(to: str, first_name: str, token: str) -> bool:
    verify_url = f"{settings.frontend_url}/verify-email?token={token}"
    subject = "Verify your GraceFinance account"

    html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#000;font-family:'Helvetica Neue',Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;padding:40px 32px;background:#0a0a0a;border:1px solid #1a1a1a;border-radius:12px;">
    <div style="width:32px;height:32px;border:1.5px solid #fff;border-radius:6px;display:flex;align-items:center;justify-content:center;margin-bottom:24px;">
      <span style="color:#fff;font-size:14px;font-weight:700;line-height:32px;display:block;text-align:center;">G</span>
    </div>
    <h1 style="color:#fff;font-size:22px;font-weight:600;margin:0 0 8px;letter-spacing:-0.5px;">Verify your email</h1>
    <p style="color:#6b7280;font-size:14px;margin:0 0 28px;line-height:1.6;">
      Hey {first_name}, welcome to GraceFinance. Click below to verify your email and activate your account.
    </p>
    <a href="{verify_url}" style="display:inline-block;padding:13px 28px;background:#fff;color:#000;text-decoration:none;border-radius:8px;font-size:14px;font-weight:700;letter-spacing:-0.2px;">
      Verify Email
    </a>
    <p style="color:#4b5563;font-size:12px;margin:24px 0 0;line-height:1.6;">
      This link expires in 24 hours. If you didn't create an account, ignore this email.
    </p>
    <hr style="border:none;border-top:1px solid #1a1a1a;margin:28px 0 20px;">
    <p style="color:#374151;font-size:11px;margin:0;">
      GraceFinance · Where Financial Confidence Is Measured.<br>
      <a href="{settings.frontend_url}" style="color:#4b5563;">gracefinance.co</a>
    </p>
  </div>
</body>
</html>
"""
    plain = f"Hey {first_name},\n\nVerify your GraceFinance account:\n{verify_url}\n\nExpires in 24 hours.\n\nGraceFinance"
    return _send(to, subject, html, plain)


def send_password_reset_email(to: str, first_name: str, token: str) -> bool:
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    subject = "Reset your GraceFinance password"

    html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#000;font-family:'Helvetica Neue',Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;padding:40px 32px;background:#0a0a0a;border:1px solid #1a1a1a;border-radius:12px;">
    <div style="width:32px;height:32px;border:1.5px solid #fff;border-radius:6px;margin-bottom:24px;">
      <span style="color:#fff;font-size:14px;font-weight:700;line-height:32px;display:block;text-align:center;">G</span>
    </div>
    <h1 style="color:#fff;font-size:22px;font-weight:600;margin:0 0 8px;letter-spacing:-0.5px;">Reset your password</h1>
    <p style="color:#6b7280;font-size:14px;margin:0 0 28px;line-height:1.6;">
      Hey {first_name}, we received a request to reset your password. Click below to set a new one.
    </p>
    <a href="{reset_url}" style="display:inline-block;padding:13px 28px;background:#fff;color:#000;text-decoration:none;border-radius:8px;font-size:14px;font-weight:700;letter-spacing:-0.2px;">
      Reset Password
    </a>
    <p style="color:#4b5563;font-size:12px;margin:24px 0 0;line-height:1.6;">
      This link expires in 30 minutes. If you didn't request this, ignore this email.
    </p>
    <hr style="border:none;border-top:1px solid #1a1a1a;margin:28px 0 20px;">
    <p style="color:#374151;font-size:11px;margin:0;">GraceFinance · <a href="{settings.frontend_url}" style="color:#4b5563;">gracefinance.co</a></p>
  </div>
</body>
</html>
"""
    plain = f"Hey {first_name},\n\nReset your GraceFinance password:\n{reset_url}\n\nExpires in 30 minutes.\n\nGraceFinance"
    return _send(to, subject, html, plain)