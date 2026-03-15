from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    description: Optional[str] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class NoteLockRequest(BaseModel):
    lock_password: Optional[str] = None  # provide to set/change lock; omit to unlock


class NoteUnlockRequest(BaseModel):
    lock_password: str


class NoteResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_locked: bool
    status: str
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PaginatedNotes(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[NoteResponse]
