from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.note import Note
from models.user import User
from core.email import send_reminder_email

scheduler = AsyncIOScheduler()


async def check_reminders():
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        notes = (
            db.query(Note)
            .filter(
                Note.reminder_at <= now,
                Note.reminder_sent == False,
                Note.is_deleted == False,
            )
            .all()
        )
        for note in notes:
            user = db.query(User).filter(User.id == note.owner_id).first()
            if user:
                try:
                    await send_reminder_email(user.email, note.title)
                    note.reminder_sent = True
                    db.commit()
                except Exception:
                    pass  # log in production
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(check_reminders, "interval", minutes=1)
    scheduler.start()
