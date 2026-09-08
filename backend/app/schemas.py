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

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Agents ---
class AgentOut(BaseModel):
    key: str
    name: str
    description: str


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
    created_at: datetime

    class Config:
        from_attributes = True
