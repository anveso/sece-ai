"""Orchestrates parse -> chunk -> embed -> persist for one uploaded document."""
import logging
import uuid

from sqlalchemy.orm import Session

from ..models import Document, DocumentChunk
from .chunking import chunk_text
from .embeddings import embed_texts
from .parsing import extract_text

logger = logging.getLogger(__name__)


def ingest_document(db: Session, document: Document, raw: bytes) -> None:
    try:
        text = extract_text(document.filename, document.content_type, raw)
        chunks = chunk_text(text)

        if not chunks:
            document.status = "error"
            document.error_message = "No extractable text found in this file."
            db.commit()
            return

        vectors = embed_texts(chunks)

        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            db.add(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    embedding=vector,
                )
            )

        document.status = "ready"
        db.commit()
    except Exception as exc:  # noqa: BLE001 - surface any failure on the document row
        logger.exception("Failed to ingest document %s", document.id)
        document.status = "error"
        document.error_message = str(exc)
        db.commit()
