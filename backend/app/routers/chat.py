"""
Streaming chat endpoint. POST /chat/stream takes a conversation_id (or none,
to start a new conversation) plus the user's message, runs the resolved
agent, and streams the assistant's reply back as Server-Sent Events so the
frontend can render tokens as they arrive, ChatGPT-style.

Multi-agent routing: if the conversation's `agent` is "auto", each message
is classified (agents/router.py) to pick a specialist from AGENT_REGISTRY;
otherwise every message uses the conversation's pinned agent. Either way,
the resolved agent key is announced via an "agent" SSE event before the
first token, and stored on the saved assistant Message so the UI can show
which specialist actually answered.
"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from sqlalchemy.orm import Session

from ..agents.registry import AGENT_REGISTRY, DEFAULT_AGENT_KEY, build_agent
from ..agents.router import classify_agent
from ..auth import get_current_user
from ..database import get_db
from ..models import Conversation, Message, User
from ..schemas import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _history_as_langchain_messages(conversation: Conversation):
    history = []
    for m in conversation.messages:
        if m.role == "user":
            history.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            history.append(AIMessage(content=m.content))
    return history


def _resolve_agent_key(conversation: Conversation, message: str) -> str:
    if conversation.agent == "auto":
        return classify_agent(message)
    if conversation.agent in AGENT_REGISTRY:
        return conversation.agent
    return DEFAULT_AGENT_KEY


@router.post("/stream")
def stream_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == payload.conversation_id,
                Conversation.user_id == current_user.id,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        requested_agent = payload.agent if payload.agent in AGENT_REGISTRY or payload.agent == "auto" else "auto"
        conversation = Conversation(user_id=current_user.id, agent=requested_agent)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    if conversation.title == "New conversation":
        conversation.title = payload.message[:60]

    user_message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    )
    db.add(user_message)
    db.commit()

    history = _history_as_langchain_messages(conversation)
    history.append(HumanMessage(content=payload.message))

    agent_key = _resolve_agent_key(conversation, payload.message)
    agent_spec = AGENT_REGISTRY[agent_key]
    agent = build_agent(agent_key, db, current_user.id)

    def event_stream():
        yield _sse("start", {"conversation_id": str(conversation.id)})
        yield _sse("agent", {"key": agent_spec.key, "name": agent_spec.name})

        full_response = ""
        try:
            # stream_mode="messages" yields (message_chunk, metadata) tuples
            # for EVERY message that passes through the graph - including the
            # input HumanMessage itself and any ToolMessage results, not just
            # the model's own output. Only AIMessageChunk instances are
            # actual assistant-generated tokens; anything else must be
            # filtered out here or it gets echoed back to the user as if the
            # assistant had said it.
            for message_chunk, _metadata in agent.stream(
                {"messages": history}, stream_mode="messages"
            ):
                if not isinstance(message_chunk, AIMessageChunk):
                    continue
                content = message_chunk.content
                if content:
                    full_response += content
                    yield _sse("token", {"content": content})
        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"detail": str(exc)})
            return

        assistant_message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
            agent=agent_key,
        )
        db.add(assistant_message)
        db.commit()

        yield _sse("done", {"message_id": str(assistant_message.id)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
