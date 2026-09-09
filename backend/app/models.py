"""
ORM models for SECE AI.

Kept deliberately small for the MVP: users, conversations + messages, and
documents + chunks (for RAG). Multi-agent metadata (which agent handled a
message) is on Message.agent so the UI/analytics can grow into it later.
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .config import settings
from .database import Base


def _uuid_col(primary_key: bool = True):
    return Column(
        UUID(as_uuid=True), primary_key=primary_key, default=uuid.uuid4, index=True
    )


class User(Base):
    __tablename__ = "users"

    id = _uuid_col()
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="student", nullable=False)  # student|faculty|admin
    is_active = Column(Boolean, default=True, nullable=False)
    # New self-registrations start unapproved and can't log in until an
    # admin approves them (see routers/auth.py::login and routers/admin.py).
    # Accounts that existed before this column was added were backfilled to
    # TRUE by the database.py migration, so nobody already using the app
    # gets locked out - only new signups from here on need approval.
    is_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = _uuid_col()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New conversation", nullable=False)
    # "auto" = the router (agents/router.py) classifies each message and
    # picks a specialist agent from AGENT_REGISTRY per turn. Any other value
    # pins every message in this conversation to that one agent key.
    agent = Column(String, default="auto", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id = _uuid_col()
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    role = Column(String, nullable=False)  # user|assistant|tool
    content = Column(Text, nullable=False)
    agent = Column(String, nullable=True)
    tool_calls = Column(Text, nullable=True)  # JSON-serialized, for debugging/audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class Document(Base):
    __tablename__ = "documents"

    id = _uuid_col()
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    status = Column(String, default="processing", nullable=False)  # processing|ready|error
    error_message = Column(Text, nullable=True)
    # Shared documents (institutional knowledge base, e.g. sece.ac.in content)
    # are searchable by every user, not just the owner - see
    # rag/retriever.py's owner_id OR is_shared filter.
    is_shared = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="documents")
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = _uuid_col()
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.embedding_dim), nullable=False)

    document = relationship("Document", back_populates="chunks")
