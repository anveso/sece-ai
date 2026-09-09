"""
Admin-only endpoints: approve/manage user accounts, monitor activity, and
oversee the knowledge base across every user (not just the caller's own).

Everything here is gated by `require_admin` - a stricter version of
`get_current_user` that 403s anyone whose role isn't "admin". There's no
separate "admin API" deployment or URL prefix trick going on; this is the
same backend, same auth, just an extra role check per route.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Conversation, Document, Message, User
from ..schemas import AdminDocumentOut, AdminSetRole, AdminUserOut

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_ROLES = {"student", "faculty", "admin"}


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


@router.get("/users", response_model=List[AdminUserOut])
def list_users(
    db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    # One query per aggregate rather than an N+1 loop per user - fine at
    # this scale (an institution's user count, not internet scale), and
    # keeps this readable. Revisit if this page ever feels slow.
    conv_counts = dict(
        db.query(Conversation.user_id, func.count(Conversation.id))
        .group_by(Conversation.user_id)
        .all()
    )
    msg_counts = dict(
        db.query(Conversation.user_id, func.count(Message.id))
        .join(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.user_id)
        .all()
    )
    last_active = dict(
        db.query(Conversation.user_id, func.max(Conversation.updated_at))
        .group_by(Conversation.user_id)
        .all()
    )

    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        AdminUserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_approved=u.is_approved,
            created_at=u.created_at,
            conversation_count=conv_counts.get(u.id, 0),
            message_count=msg_counts.get(u.id, 0),
            last_active=last_active.get(u.id),
        )
        for u in users
    ]


@router.post("/users/{user_id}/approve", response_model=AdminUserOut)
def approve_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_approved = True
    db.commit()
    db.refresh(user)
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_approved=user.is_approved,
        created_at=user.created_at,
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserOut)
def set_user_role(
    user_id: uuid.UUID,
    payload: AdminSetRole,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"role must be one of {sorted(VALID_ROLES)}",
        )
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and payload.role != "admin":
        # Prevents an admin from locking themselves out by accident (there's
        # no "undo" here without direct DB access) - demoting yourself has
        # to happen from a *different* admin account.
        raise HTTPException(
            status_code=400, detail="You can't change your own role."
        )
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_approved=user.is_approved,
        created_at=user.created_at,
    )


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own account.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Cascades to their conversations/messages/documents via the
    # relationship(cascade="all, delete-orphan") settings on User in
    # models.py - also removes any shared documents only they had access
    # to delete otherwise, which is the right behavior for "reject/remove
    # this account" rather than orphaning their data.
    db.delete(user)
    db.commit()
    return None


@router.get("/documents", response_model=List[AdminDocumentOut])
def list_all_documents(
    db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    # Unlike GET /documents (scoped to the caller's own uploads), this spans
    # every user's documents - shared and private alike - so admin can see
    # and moderate the whole knowledge base, not just what they personally
    # added. Deleting still goes through the existing DELETE /documents/{id}
    # (already admin-aware - see routers/documents.py).
    rows = (
        db.query(Document, User.email)
        .join(User, User.id == Document.owner_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        AdminDocumentOut(
            id=doc.id,
            filename=doc.filename,
            content_type=doc.content_type,
            status=doc.status,
            error_message=doc.error_message,
            is_shared=doc.is_shared,
            created_at=doc.created_at,
            owner_email=owner_email,
        )
        for doc, owner_email in rows
    ]
