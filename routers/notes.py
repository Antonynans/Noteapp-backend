from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
import math

from db.database import get_db
from models.note import Note
from models.user import User
from schemas.note import (
    NoteCreate, NoteUpdate, NoteResponse,
    PaginatedNotes, NoteLockRequest, NoteUnlockRequest
)
from core.security import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/notes", tags=["Notes"])


def get_note_or_404(note_id: int, user: User, db: Session) -> Note:
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user.id
    ).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.get("", response_model=PaginatedNotes)
def list_notes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    search: str = Query(None, description="Search by title or description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all notes for the current user with pagination and search."""
    query = db.query(Note).filter(Note.owner_id == current_user.id)

    if search:
        query = query.filter(
            or_(
                Note.title.ilike(f"%{search}%"),
                Note.description.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    notes = (
        query
        .order_by(Note.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": notes,
    }


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new note."""
    note = Note(
        title=payload.title,
        description=payload.description,
        owner_id=current_user.id,
        status="Created",
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single note by ID."""
    return get_note_or_404(note_id, current_user, db)


@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a note's title or description."""
    note = get_note_or_404(note_id, current_user, db)

    if note.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unlock the note before editing"
        )

    if payload.title is not None:
        note.title = payload.title
    if payload.description is not None:
        note.description = payload.description

    note.status = "Updated"
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a note permanently."""
    note = get_note_or_404(note_id, current_user, db)

    if note.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unlock the note before deleting"
        )

    db.delete(note)
    db.commit()


@router.post("/{note_id}/lock", response_model=NoteResponse)
def lock_note(
    note_id: int,
    payload: NoteLockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lock a note. Optionally set a lock password."""
    note = get_note_or_404(note_id, current_user, db)

    note.is_locked = True
    if payload.lock_password:
        note.lock_password = hash_password(payload.lock_password)

    db.commit()
    db.refresh(note)
    return note


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note is not locked"
        )

    if note.lock_password and not verify_password(payload.lock_password, note.lock_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect lock password"
        )

    note.is_locked = False
    db.commit()
    db.refresh(note)
    return note
