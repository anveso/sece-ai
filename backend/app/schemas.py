"""Pydantic request/response schemas."""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None
    role: str = "student"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str]
    role: str
    is_approved: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterOut(BaseModel):
    message: str
    user: UserOut


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Admin ---
class AdminUserOut(UserOut):
    conversation_count: int = 0
    message_count: int = 0
    last_active: Optional[datetime] = None


class AdminSetRole(BaseModel):
    role: str  # student|faculty|admin


# --- Agents ---
class AgentOut(BaseModel):
    key: str
    name: str
    description: str
    group: str = "General"


# --- Conversations ---
class ConversationCreate(BaseModel):
    title: Optional[str] = None
    agent: str = "auto"


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    agent: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    agent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(ConversationOut):
    messages: List[MessageOut] = []


# --- Chat ---
class ChatRequest(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    message: str
    # Only used when conversation_id is omitted (i.e. creating a new
    # conversation). "auto" lets the router pick an agent per message;
    # any other AGENT_REGISTRY key pins the whole conversation to it.
    agent: str = "auto"


# --- Documents ---
class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: Optional[str]
    status: str
    error_message: Optional[str] = None
    is_shared: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AdminDocumentOut(DocumentOut):
    # Admin's document-management view spans every user's documents, not
    # just the caller's own - this is what identifies whose it is.
    owner_email: str
