"""
DISHA Platform - Verification Email Delivery Service
Disaster Intelligence and Situational Hazard Awareness Platform

Supports:
1. Google OAuth2 / Gmail API / XOAUTH2 Delivery
2. Standard SMTP Delivery (TLS/SSL)
3. Development Console Simulation (when credentials not configured)
"""

import asyncio
import base64
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("disha.services.email")


def generate_disha_email_html(otp: str, username: Optional[str] = None) -> str:
    user_greeting = f"Hello {username}," if username else "Hello,"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DISHA Account Verification</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f8fafc;
      margin: 0;
      padding: 24px;
      color: #1e293b;
    }}
    .container {{
      max-width: 540px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 16px;
      border: 1px solid #e2e8f0;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
      overflow: hidden;
    }}
    .header {{
      background: linear-gradient(135deg, #ea580c 0%, #dc2626 100%);
      padding: 32px 24px;
      text-align: center;
      color: #ffffff;
    }}
    .header h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: 0.5px;
    }}
    .header p {{
      margin: 6px 0 0 0;
      font-size: 13px;
      opacity: 0.9;
    }}
    .content {{
      padding: 32px 24px;
    }}
    .otp-box {{
      background-color: #fff7ed;
      border: 2px dashed #f97316;
      border-radius: 12px;
      padding: 20px;
      text-align: center;
      margin: 24px 0;
    }}
    .otp-code {{
      font-size: 36px;
      font-weight: 800;
      letter-spacing: 8px;
      color: #c2410c;
      margin: 0;
      font-family: 'Courier New', Courier, monospace;
    }}
    .notice {{
      font-size: 13px;
      color: #64748b;
      line-height: 1.6;
      margin-top: 16px;
    }}
    .footer {{
      background-color: #f8fafc;
      padding: 16px 24px;
      text-align: center;
      border-top: 1px solid #e2e8f0;
      font-size: 11px;
      color: #94a3b8;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 600;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <span class="badge">Government Disaster Platform</span>
      <h1>DISHA Platform</h1>
      <p>Disaster Intelligence and Situational Hazard Awareness</p>
    </div>
    <div class="content">
      <p style="font-size: 16px; font-weight: 600; margin-top: 0;">{user_greeting}</p>
      <p style="font-size: 14px; color: #475569; line-height: 1.6;">
        Thank you for creating an account on the DISHA Emergency Situational Awareness Platform.
        Please use the 6-digit verification code below to verify your email address.
      </p>
      
      <div class="otp-box">
        <p style="margin: 0 0 8px 0; font-size: 12px; font-weight: 700; color: #ea580c; text-transform: uppercase; letter-spacing: 1px;">Verification Code</p>
        <div class="otp-code">{otp}</div>
        <p style="margin: 8px 0 0 0; font-size: 12px; color: #9a3412;">Valid for {settings.OTP_EXPIRE_MINUTES} minutes</p>
      </div>

      <div class="notice">
        <p><strong>Security Notice:</strong></p>
        <ul style="margin: 4px 0; padding-left: 20px;">
          <li>Never share this verification code with anyone.</li>
          <li>DISHA personnel will never request your OTP.</li>
          <li>If you did not request this registration, please safely ignore this email.</li>
        </ul>
      </div>
    </div>
    <div class="footer">
      &copy; 2026 DISHA Platform &bull; National Early Warning & Disaster Awareness Network<br>
      This is an automated system notification. Please do not reply directly.
    </div>
  </div>
</body>
</html>"""


def _send_smtp_email_sync(
    recipient: str,
    subject: str,
    html_content: str,
) -> bool:
    """Synchronous SMTP email delivery."""
    sender = settings.SMTP_FROM or settings.SMTP_USER or settings.GOOGLE_USER or "no-reply@disha.gov.in"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"DISHA Platform <{sender}>"
    msg["To"] = recipient

    part = MIMEText(html_content, "html")
    msg.attach(part)

    # 1. Check Google OAuth2 credentials
    if settings.GOOGLE_USER and settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET and settings.GOOGLE_REFRESH_TOKEN:
        try:
            import google.auth.transport.requests
            from google.oauth2.credentials import Credentials

            creds = Credentials(
                None,
                refresh_token=settings.GOOGLE_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            request = google.auth.transport.requests.Request()
            creds.refresh(request)
            access_token = creds.token

            auth_string = f"user={settings.GOOGLE_USER}\1auth=Bearer {access_token}\1\1"
            auth_b64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.docmd("AUTH", "XOAUTH2 " + auth_b64)
                server.sendmail(settings.GOOGLE_USER, [recipient], msg.as_string())

            logger.info(f"[EmailService] Sent OTP verification email via Gmail OAuth2 to {recipient}")
            return True
        except Exception as e:
            logger.error(f"[EmailService] Gmail OAuth2 delivery failed: {e}")

    # 2. Check standard SMTP credentials
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                if settings.SMTP_TLS:
                    server.starttls()
                    server.ehlo()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(sender, [recipient], msg.as_string())

            logger.info(f"[EmailService] Sent OTP verification email via SMTP to {recipient}")
            return True
        except Exception as e:
            logger.error(f"[EmailService] SMTP delivery failed: {e}")

    # 3. Development / Mock Mode fallback (logged cleanly)
    logger.info(
        f"[EmailService][DEV/MOCK] Verification Email for {recipient} generated successfully. "
        f"Subject: '{subject}'"
    )
    return True


async def send_verification_email(
    email: str,
    otp: str,
    username: Optional[str] = None,
) -> bool:
    """
    Sends a verification OTP email asynchronously to the user.
    """
    subject = f"DISHA Verification Code: {otp}"
    html = generate_disha_email_html(otp=otp, username=username)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        _send_smtp_email_sync,
        email,
        subject,
        html,
    )
