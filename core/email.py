import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings

FROM_ADDRESS = settings.BREVO_SMTP_USER


def _get_smtp_client():
    """Get Brevo SMTP client."""
    server = smtplib.SMTP("smtp-relay.brevo.com", 587)
    server.starttls()
    server.login(settings.BREVO_SMTP_USER, settings.BREVO_SMTP_PASSWORD)
    return server


def _send_email(to_email: str, subject: str, html_body: str):
    """Send an email via Brevo SMTP."""
    msg = MIMEMultipart()
    msg["From"] = f"Quill <{FROM_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    server = _get_smtp_client()
    try:
        server.send_message(msg)
    finally:
        server.quit()


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
