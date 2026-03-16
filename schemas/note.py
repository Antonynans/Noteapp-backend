from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    description: Optional[str] = None   
    colour: Optional[str] = "#ffffff"
    tags: Optional[List[str]] = []
    reminder_at: Optional[datetime] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    colour: Optional[str] = None
    tags: Optional[List[str]] = None
    reminder_at: Optional[datetime] = None


class NoteLockRequest(BaseModel):
    lock_password: Optional[str] = None


class NoteUnlockRequest(BaseModel):
    lock_password: str


class NoteResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    description_html: Optional[str]
    status: str
    colour: str
    is_pinned: bool
    is_locked: bool
    is_shared: bool
    share_token: Optional[str]
    tags: Optional[List[str]]
    reminder_at: Optional[datetime]
    reminder_sent: bool
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_tags(cls, note):
        data = {
            "id": note.id,
            "title": note.title,
            "description": note.description,
            "description_html": note.description_html,
            "status": note.status,
            "colour": note.colour or "#ffffff",
            "is_pinned": note.is_pinned,
            "is_locked": note.is_locked,
            "is_shared": note.is_shared,
            "share_token": note.share_token if note.is_shared else None,
            "tags": note.tags.split(",") if note.tags else [],
            "reminder_at": note.reminder_at,
            "reminder_sent": note.reminder_sent,
            "owner_id": note.owner_id,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
        }
        return cls(**data)


class PaginatedNotes(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[NoteResponse]


class SharedNoteResponse(BaseModel):
    id: int
    title: str
    description_html: Optional[str]
    colour: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
