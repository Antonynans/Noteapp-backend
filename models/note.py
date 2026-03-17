from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from db.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)        
    description_html = Column(Text, nullable=True)   

    status = Column(String(50), default="Created")  
    colour = Column(String(20), default="#ffffff")  
    is_pinned = Column(Boolean, default=False)
    position = Column(Integer, default=0, nullable=False)
    is_locked = Column(Boolean, default=False)
    lock_password = Column(String, nullable=True)

    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    share_token = Column(String, unique=True, nullable=True, index=True)
    is_shared = Column(Boolean, default=False)

    reminder_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent = Column(Boolean, default=False)

    tags = Column(String, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", backref="notes")
