import httpx
from core.config import settings

FROM_EMAIL = "antonynans@gmail.com"  # your verified Brevo sender
FROM_NAME = "Quill"
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _send_email(to_email: str, subject: str, html_body: str):
    """Send email via Brevo HTTP API (port 443 — works on Render free tier)."""
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }

    response = httpx.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
    response.raise_for_status()


async def send_verification_email(email: str, token: str, full_name: str = None):
    verify_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    name = full_name or "there"

    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;">
      <h2 style="color:#f97316;margin-bottom:8px;">Welcome to Quill 👋</h2>
      <p style="color:#374151;">Hi {name},</p>
      <p style="color:#374151;">
        Thanks for signing up. Please verify your email address to activate your account.
      </p>
      <p style="margin:32px 0;">
        <a href="{verify_url}"
           style="background:#f97316;color:white;padding:14px 28px;border-radius:6px;
                  text-decoration:none;font-weight:bold;display:inline-block;">
          Verify Email Address
        </a>
      </p>
      <p style="color:#9ca3af;font-size:13px;">This link expires in 24 hours.</p>
      <p style="color:#9ca3af;font-size:13px;">
        If you didn't create an account, you can safely ignore this email.
      </p>
      <hr style="border:none;border-top:1px solid #f3f4f6;margin:24px 0;"/>
      <p style="color:#d1d5db;font-size:12px;">Quill — Your notes, organised.</p>
    </div>
    """

    try:
        _send_email(email, "Verify your Quill account", body)
    except Exception as e:
        print(f"[email] Failed to send verification email to {email}: {e}")


async def send_password_reset_email(email: str, token: str):
    reset_url = f"{settings.BASE_URL}/api/auth/reset-password?token={token}"

    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;">
      <h2 style="color:#f97316;margin-bottom:8px;">Reset your password</h2>
      <p style="color:#374151;">
        You requested a password reset. Click the button below to set a new password.
      </p>
      <p style="margin:32px 0;">
        <a href="{reset_url}"
           style="background:#f97316;color:white;padding:14px 28px;border-radius:6px;
                  text-decoration:none;font-weight:bold;display:inline-block;">
          Reset Password
        </a>
      </p>
      <p style="color:#9ca3af;font-size:13px;">This link expires in 1 hour.</p>
      <p style="color:#9ca3af;font-size:13px;">
        If you did not request this, your password won't change — you can ignore this email.
      </p>
      <hr style="border:none;border-top:1px solid #f3f4f6;margin:24px 0;"/>
      <p style="color:#d1d5db;font-size:12px;">Quill — Your notes, organised.</p>
    </div>
    """

    try:
        _send_email(email, "Reset your Quill password", body)
    except Exception as e:
        print(f"[email] Failed to send reset email to {email}: {e}")


async def send_reminder_email(email: str, note_title: str):
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;">
      <h2 style="color:#f97316;margin-bottom:8px;">Note Reminder</h2>
      <p style="color:#374151;">
        This is your reminder for: <strong>{note_title}</strong>
      </p>
      <p style="color:#374151;">Open Quill to view it.</p>
      <hr style="border:none;border-top:1px solid #f3f4f6;margin:24px 0;"/>
      <p style="color:#d1d5db;font-size:12px;">Quill — Your notes, organised.</p>
    </div>
    """

    try:
        _send_email(email, f"Reminder: {note_title}", body)
    except Exception as e:
        print(f"[email] Failed to send reminder email to {email}: {e}")