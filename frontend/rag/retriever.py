"""pgvector similarity search over a user's ingested documents."""
from typing import List, TypedDict
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import Document, DocumentChunk
from .embeddings import embed_query


class RetrievedChunk(TypedDict):
    document_id: str
    filename: str
    content: str
    distance: float


def retrieve_relevant_chunks(
    db: Session, user_id: UUID, query: str, top_k: int = 5
) -> List[RetrievedChunk]:
    query_vector = embed_query(query)

    results = (
        db.query(
            DocumentChunk.content,
            DocumentChunk.document_id,
            Document.filename,
            DocumentChunk.embedding.cosine_distance(query_vector).label("distance"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(
            (Document.owner_id == user_id) | (Document.is_shared.is_(True)),
            Document.status == "ready",
        )
        .order_by("distance")
        .limit(top_k)
        .all()
    )

    return [
        RetrievedChunk(
            document_id=str(doc_id),
            filename=filename,
            content=content,
            distance=float(distance),
        )
        for content, doc_id, filename, distance in results
    ]
