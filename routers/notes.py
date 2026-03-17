import secrets
import math
import markdown
import bleach
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from db.database import get_db
from models.note import Note
from models.user import User
from schemas.note import (
    NoteCreate, NoteUpdate, NoteResponse, PaginatedNotes,
    NoteLockRequest, NoteUnlockRequest, SharedNoteResponse
)
from core.security import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/notes", tags=["Notes"])

ALLOWED_COLOURS = {
    "#ffffff", "#fef9c3", "#dcfce7", "#dbeafe",
    "#fce7f3", "#ede9fe", "#ffedd5", "#f1f5f9"
}


def render_markdown(text: str) -> str:
    """Convert markdown to sanitized HTML."""
    raw_html = markdown.markdown(text, extensions=["fenced_code", "tables", "nl2br"])
    allowed_tags = [
        "p", "h1", "h2", "h3", "h4", "h5", "h6",
        "strong", "em", "ul", "ol", "li", "code",
        "pre", "blockquote", "a", "br", "table",
        "thead", "tbody", "tr", "th", "td", "hr"
    ]
    return bleach.clean(raw_html, tags=allowed_tags, strip=True)


def get_note_or_404(note_id: int, user: User, db: Session) -> Note:
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user.id,
        Note.is_deleted == False,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def serialize_note(note: Note) -> NoteResponse:
    return NoteResponse.from_orm_with_tags(note)


def move_note_to_position(
    note: Note, new_position: int, user: User, db: Session
) -> None:
    """
    Move a note to a new position, adjusting other notes as needed.
    Only affects notes in the range between old and new position.
    """
    old_position = note.position
    
    if old_position == new_position:
        return  
    
    all_notes = db.query(Note).filter(
        Note.owner_id == user.id,
        Note.is_deleted == False,
        Note.id != note.id,
    ).all()
    
    if old_position < new_position:
        for n in all_notes:
            if old_position < n.position <= new_position:
                n.position -= 1
    else:
        for n in all_notes:
            if new_position <= n.position < old_position:
                n.position += 1
    
    note.position = new_position


def move_note_to_first(note: Note, user: User, db: Session) -> None:
    """
    Move a note to the first position (position 1), shifting others down.
    """
    if note.position == 1:
        return  
    
    db.query(Note).filter(
        Note.owner_id == user.id,
        Note.is_deleted == False,
        Note.id != note.id,
        Note.position < note.position,
    ).update({Note.position: Note.position + 1}, synchronize_session=False)
    
    note.position = 1


@router.get("", response_model=PaginatedNotes)
def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    search: str = Query(None, description="Search title, description, or tags"),
    colour: str = Query(None, description="Filter by colour hex"),
    tag: str = Query(None, description="Filter by tag"),
    pinned_only: bool = Query(False, description="Only return pinned notes"),
    sort_by: str = Query("position", description="Sort field: position, created_at, updated_at, title"),
    sort_order: str = Query("asc", description="asc or desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notes with pagination, search, filtering, and sorting."""
    query = db.query(Note).filter(
        Note.owner_id == current_user.id,
        Note.is_deleted == False,
    )

    if search:
        query = query.filter(
            or_(
                Note.title.ilike(f"%{search}%"),
                Note.description.ilike(f"%{search}%"),
                Note.tags.ilike(f"%{search}%"),
            )
        )
    if colour:
        query = query.filter(Note.colour == colour)
    if tag:
        query = query.filter(Note.tags.ilike(f"%{tag}%"))
    if pinned_only:
        query = query.filter(Note.is_pinned == True)

    sort_col = getattr(Note, sort_by, Note.created_at)
    query = query.order_by(
        Note.is_pinned.desc(), 
        sort_col.desc() if sort_order == "desc" else sort_col.asc(),
    )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    notes = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": [serialize_note(n) for n in notes],
    }


@router.post("", response_model=NoteResponse, status_code=201)
def create_note(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new note with optional markdown, colour, tags, and reminder."""
    # Increment positions of all existing notes to make room for new one at position 1
    db.query(Note).filter(
        Note.owner_id == current_user.id,
        Note.is_deleted == False,
    ).update({Note.position: Note.position + 1}, synchronize_session=False)
    
    note = Note(
        title=payload.title,
        description=payload.description,
        description_html=render_markdown(payload.description) if payload.description else None,
        colour=payload.colour or "#ffffff",
        position=1,  
        tags=",".join(payload.tags) if payload.tags else None,
        reminder_at=payload.reminder_at,
        owner_id=current_user.id,
        status="Created",
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return serialize_note(note)


@router.get("/trash", response_model=PaginatedNotes)
def list_trash(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List soft-deleted notes in the trash."""
    query = db.query(Note).filter(
        Note.owner_id == current_user.id,
        Note.is_deleted == True,
    ).order_by(Note.deleted_at.desc())

    total = query.count()
    notes = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 1,
        "items": [serialize_note(n) for n in notes],
    }


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single note."""
    return serialize_note(get_note_or_404(note_id, current_user, db))


@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a note."""
    note = get_note_or_404(note_id, current_user, db)

    if note.is_locked:
        raise HTTPException(status_code=403, detail="Unlock the note before editing")

    if payload.position is not None:
        move_note_to_position(note, payload.position, current_user, db)
    else:
        is_updating_content = any([
            payload.title is not None,
            payload.description is not None,
            payload.colour is not None,
            payload.tags is not None,
            payload.reminder_at is not None,
        ])
        if is_updating_content:
            move_note_to_first(note, current_user, db)

    if payload.title is not None:
        note.title = payload.title
    if payload.description is not None:
        note.description = payload.description
        note.description_html = render_markdown(payload.description)
    if payload.colour is not None:
        note.colour = payload.colour
    if payload.tags is not None:
        note.tags = ",".join(payload.tags)
    if payload.reminder_at is not None:
        note.reminder_at = payload.reminder_at
        note.reminder_sent = False

    note.status = "Updated"
    db.commit()
    db.refresh(note)
    return serialize_note(note)


@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete — moves note to trash."""
    note = get_note_or_404(note_id, current_user, db)
    if note.is_locked:
        raise HTTPException(status_code=403, detail="Unlock the note before deleting")

    note.is_deleted = True
    note.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.delete("/{note_id}/permanent", status_code=204)
def permanent_delete(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a note from trash."""
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == current_user.id,
        Note.is_deleted == True,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found in trash")
    db.delete(note)
    db.commit()


@router.post("/{note_id}/restore", response_model=NoteResponse)
def restore_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Restore a note from trash."""
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == current_user.id,
        Note.is_deleted == True,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found in trash")
    note.is_deleted = False
    note.deleted_at = None
    db.commit()
    db.refresh(note)
    return serialize_note(note)


@router.post("/{note_id}/pin", response_model=NoteResponse)
def toggle_pin(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggle pin status on a note."""
    note = get_note_or_404(note_id, current_user, db)
    note.is_pinned = not note.is_pinned
    db.commit()
    db.refresh(note)
    return serialize_note(note)


@router.post("/{note_id}/lock", response_model=NoteResponse)
def lock_note(
    note_id: int,
    payload: NoteLockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lock a note with an optional password."""
    note = get_note_or_404(note_id, current_user, db)
    note.is_locked = True
    if payload.lock_password:
        note.lock_password = hash_password(payload.lock_password)
    db.commit()
    db.refresh(note)
    return serialize_note(note)


@router.post("/{note_id}/unlock", response_model=NoteResponse)
def unlock_note(
    note_id: int,
    payload: NoteUnlockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlock a note using the lock password."""
    note = get_note_or_404(note_id, current_user, db)
    if not note.is_locked:
        raise HTTPException(status_code=400, detail="Note is not locked")
    if note.lock_password and not verify_password(payload.lock_password, note.lock_password):
        raise HTTPException(status_code=403, detail="Incorrect lock password")
    note.is_locked = False
    db.commit()
    db.refresh(note)
    return serialize_note(note)


@router.post("/{note_id}/share", response_model=NoteResponse)
def share_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a public share link for a note."""
    note = get_note_or_404(note_id, current_user, db)
    if not note.share_token:
        note.share_token = secrets.token_urlsafe(24)
    note.is_shared = True
    db.commit()
    db.refresh(note)
    return serialize_note(note)


@router.post("/{note_id}/unshare", response_model=NoteResponse)
def unshare_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke the public share link for a note."""
    note = get_note_or_404(note_id, current_user, db)
    note.is_shared = False
    note.share_token = None
    db.commit()
    db.refresh(note)
    return serialize_note(note)


@router.get("/shared/{token}", response_model=SharedNoteResponse)
def view_shared_note(token: str, db: Session = Depends(get_db)):
    """Public endpoint — view a shared note via its token. No auth required."""
    note = db.query(Note).filter(
        Note.share_token == token,
        Note.is_shared == True,
        Note.is_deleted == False,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Shared note not found or link revoked")
    return note

