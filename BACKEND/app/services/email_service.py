"""
DISHA Platform - Verification Email Delivery Service
Disaster Intelligence and Situational Hazard Awareness Platform

Supports:
1. Brevo (Sendinblue) Transactional HTTPS API Delivery (with HTML + Plain-Text multipart for maximum deliverability)
2. Development Console Simulation (when credentials not configured)
"""

import asyncio
import logging
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("disha.services.email")


def mask_recipient(recipient: str) -> str:
    """Masks recipient email for safe diagnostic logging."""
    if not recipient or "@" not in recipient:
        return "******"
    user_part, domain = recipient.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "*"
    else:
        masked_user = user_part[0] + "*" * min(4, len(user_part) - 2) + user_part[-1]
    return f"{masked_user}@{domain}"


def generate_disha_email_text(otp: str, username: Optional[str] = None) -> str:
    """Generates clean plain-text fallback content to prevent spam filter penalization."""
    user_greeting = f"Hello {username}," if username else "Hello,"
    return (
        f"DISHA Platform Account Verification\n"
        f"National Disaster Intelligence and Situational Hazard Awareness\n\n"
        f"{user_greeting}\n\n"
        f"Thank you for creating an account on the DISHA Emergency Situational Awareness Platform.\n\n"
        f"Your 6-digit verification code is: {otp}\n\n"
        f"This code is valid for {settings.OTP_EXPIRE_MINUTES} minutes.\n\n"
        f"Security Notice:\n"
        f"- Never share this verification code with anyone.\n"
        f"- DISHA personnel will never request your OTP.\n"
        f"- If you did not request this registration, please safely ignore this email.\n\n"
        f"— DISHA Platform Team\n"
        f"National Early Warning & Disaster Awareness Network"
    )


def generate_disha_email_html(otp: str, username: Optional[str] = None) -> str:
    """Generates official DISHA branded HTML verification template."""
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


def _send_brevo_email_sync(
    recipient: str,
    subject: str,
    html_content: str,
    otp: Optional[str] = None,
    username: Optional[str] = None,
) -> bool:
    """Synchronous Brevo HTTPS API delivery helper."""
    clean_recipient = recipient.strip().lower()
    masked = mask_recipient(clean_recipient)
    logger.info("OTP delivery request initiated for recipient: %s", masked)

    # 1. Brevo HTTPS API delivery
    if settings.BREVO_API_KEY:
        sender_email = (
            (settings.BREVO_SENDER_EMAIL or "").strip()
            or (settings.SMTP_FROM or "").strip()
            or (settings.SMTP_USER or "").strip()
            or "no-reply@disha.gov.in"
        )
        sender_name = settings.BREVO_SENDER_NAME or "DISHA Platform"

        logger.info(
            "Provider: Brevo HTTPS API (Endpoint: https://api.brevo.com/v3/smtp/email as '%s' <%s>)",
            sender_name,
            sender_email,
        )

        headers = {
            "api-key": settings.BREVO_API_KEY.strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        text_content = generate_disha_email_text(otp=otp or "------", username=username)

        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email,
            },
            "to": [
                {
                    "email": clean_recipient,
                    "name": username or "User",
                }
            ],
            "replyTo": {
                "name": sender_name,
                "email": sender_email,
            },
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers=headers,
                    json=payload,
                )

            if res.status_code in (200, 201, 202):
                msg_id = ""
                try:
                    msg_id = res.json().get("messageId", "")
                except Exception:
                    pass
                logger.info(
                    "Email delivery status: %s (Accepted by Brevo HTTPS API for %s, messageId: %s)",
                    res.status_code,
                    masked,
                    msg_id,
                )
                return True

            try:
                err_data = res.json()
                code = err_data.get("code", f"HTTP_{res.status_code}")
                msg = err_data.get("message", res.text[:200])
            except Exception:
                code = f"HTTP_{res.status_code}"
                msg = res.text[:200]

            logger.error(
                "Brevo HTTPS API delivery failed for %s (Status: %s, Code: '%s'): %s",
                masked,
                res.status_code,
                code,
                msg,
            )

            if res.status_code in (400, 401, 403) or "sender" in msg.lower():
                logger.warning(
                    "Note: Ensure the sender email '%s' is registered and verified in your Brevo account (https://app.brevo.com/senders).",
                    sender_email,
                )
            return False

        except httpx.RequestError as exc:
            logger.error(
                "Brevo HTTPS API connection error for %s: %s",
                masked,
                str(exc).splitlines()[0],
            )
            return False
        except Exception as exc:
            logger.exception("Unexpected error dispatching email via Brevo HTTPS API: %s", exc)
            return False

    # 2. Development Mode Simulation fallback
    if not settings.is_production:
        logger.info("Provider: Local Development Console Simulation")
        logger.info(
            "[EmailService][DEV MODE] Verification OTP generated for %s (Subject: '%s')",
            masked,
            subject,
        )
        return True

    # 3. Production unconfigured warning
    logger.error(
        "Email delivery failed in production: BREVO_API_KEY is not configured. "
        "Please add BREVO_API_KEY, BREVO_SENDER_EMAIL, and BREVO_SENDER_NAME to your Render dashboard."
    )
    return False


# Legacy alias for backward compatibility with existing unit test fixtures
_send_smtp_email_sync = _send_brevo_email_sync


async def send_verification_email(
    email: str,
    otp: str,
    username: Optional[str] = None,
) -> bool:
    """
    Sends a verification OTP email asynchronously using the Brevo HTTPS Transactional API.
    """
    clean_recipient = email.strip().lower()
    masked = mask_recipient(clean_recipient)
    subject = f"DISHA Verification Code: {otp}"
    html = generate_disha_email_html(otp=otp, username=username)
    text = generate_disha_email_text(otp=otp, username=username)

    logger.info("OTP delivery request initiated for recipient: %s", masked)

    # 1. Brevo HTTPS Transactional API Delivery
    if settings.BREVO_API_KEY:
        sender_email = (
            (settings.BREVO_SENDER_EMAIL or "").strip()
            or (settings.SMTP_FROM or "").strip()
            or (settings.SMTP_USER or "").strip()
            or "no-reply@disha.gov.in"
        )
        sender_name = settings.BREVO_SENDER_NAME or "DISHA Platform"

        logger.info(
            "Provider: Brevo HTTPS API (Endpoint: https://api.brevo.com/v3/smtp/email as '%s' <%s>)",
            sender_name,
            sender_email,
        )

        headers = {
            "api-key": settings.BREVO_API_KEY.strip(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "sender": {
                "name": sender_name,
                "email": sender_email,
            },
            "to": [
                {
                    "email": clean_recipient,
                    "name": username or "User",
                }
            ],
            "replyTo": {
                "name": sender_name,
                "email": sender_email,
            },
            "subject": subject,
            "htmlContent": html,
            "textContent": text,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers=headers,
                    json=payload,
                )

            if res.status_code in (200, 201, 202):
                msg_id = ""
                try:
                    msg_id = res.json().get("messageId", "")
                except Exception:
                    pass
                logger.info(
                    "Email delivery status: %s (Accepted by Brevo HTTPS API for %s, messageId: %s)",
                    res.status_code,
                    masked,
                    msg_id,
                )
                return True

            try:
                err_data = res.json()
                code = err_data.get("code", f"HTTP_{res.status_code}")
                msg = err_data.get("message", res.text[:200])
            except Exception:
                code = f"HTTP_{res.status_code}"
                msg = res.text[:200]

            logger.error(
                "Brevo HTTPS API delivery failed for %s (Status: %s, Code: '%s'): %s",
                masked,
                res.status_code,
                code,
                msg,
            )

            if res.status_code in (400, 401, 403) or "sender" in msg.lower():
                logger.warning(
                    "Note: Ensure the sender email '%s' is registered and verified in your Brevo account (https://app.brevo.com/senders).",
                    sender_email,
                )
            return False

        except httpx.RequestError as exc:
            logger.error(
                "Brevo HTTPS API connection error for %s: %s",
                masked,
                str(exc).splitlines()[0],
            )
            return False
        except Exception as exc:
            logger.exception("Unexpected error dispatching email via Brevo HTTPS API: %s", exc)
            return False

    # 2. Development Mode Simulation fallback
    if not settings.is_production:
        logger.info("Provider: Local Development Console Simulation")
        logger.info(
            "[EmailService][DEV MODE] Verification OTP generated for %s (Subject: '%s')",
            masked,
            subject,
        )
        return True

    # 3. Production unconfigured warning
    logger.error(
        "Email delivery failed in production: BREVO_API_KEY is not configured. "
        "Please add BREVO_API_KEY, BREVO_SENDER_EMAIL, and BREVO_SENDER_NAME to your Render dashboard."
    )
    return False
