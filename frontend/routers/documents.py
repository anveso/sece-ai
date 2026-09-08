"""Upload institutional documents for RAG, list them, check status, delete them."""
import os
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import Document, User
from ..rag.ingest import ingest_document
from ..schemas import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"}


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile,
    shared: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    # Shared docs land in everyone's search results (see rag/retriever.py),
    # so only faculty/admin accounts can mark an upload as shared - a
    # student's own upload always stays private to them.
    if shared and current_user.role not in ("faculty", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Only faculty/admin accounts can add shared institutional documents.",
        )

    raw = await file.read()

    document = Document(
        id=uuid.uuid4(),
        owner_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type,
        status="processing",
        is_shared=shared,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Keep a copy on disk too (useful for re-processing / MinIO migration later).
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(os.path.join(settings.upload_dir, f"{document.id}{ext}"), "wb") as f:
        f.write(raw)

    # MVP: ingest synchronously. Move this to a background task/worker queue
    # once uploads are large/frequent enough that request latency matters.
    ingest_document(db, document, raw)
    db.refresh(document)

    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()
    return None
