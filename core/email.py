from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
)


async def send_password_reset_email(email: str, token: str):
    reset_url = f"{settings.BASE_URL}/auth/reset-password?token={token}"
    body = f"""
    <h2>DevNote — Password Reset</h2>
    <p>You requested a password reset. Click the link below to reset your password.</p>
    <p><a href="{reset_url}" style="background:#f97316;color:white;padding:10px 20px;border-radius:5px;text-decoration:none;">Reset Password</a></p>
    <p>This link expires in 1 hour.</p>
    <p>If you did not request this, ignore this email.</p>
    """
    message = MessageSchema(
        subject="DevNote — Reset Your Password",
        recipients=[email],
        body=body,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)


async def send_reminder_email(email: str, note_title: str):
    body = f"""
    <h2>DevNote — Note Reminder</h2>
    <p>This is your reminder for the note: <strong>{note_title}</strong></p>
    <p>Open DevNote to view it.</p>
    """
    message = MessageSchema(
        subject=f"DevNote Reminder: {note_title}",
        recipients=[email],
        body=body,
        subtype=MessageType.html,
    )
    fm = FastMail(conf)
    await fm.send_message(message)
