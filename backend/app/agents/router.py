"""
The routing classifier used when a conversation is set to "auto": a cheap,
single LLM call that picks which specialist agent should handle the user's
latest message. Falls back to the default agent on any ambiguity or error,
so a routing hiccup never blocks the chat.
"""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..config import settings
from .registry import AGENT_REGISTRY, DEFAULT_AGENT_KEY

_ROUTER_PROMPT_TEMPLATE = """You are a routing classifier for SECE AI, a college \
assistant platform with multiple specialist agents. Given the user's latest \
message, choose exactly ONE agent key that should handle it.

Available agents:
{agent_list}

Respond with ONLY the agent key from the list above, nothing else - no \
punctuation, no explanation. If you are unsure, respond with "{default_key}".
"""


def _agent_list_text() -> str:
    return "\n".join(
        f"- {spec.key}: {spec.description}" for spec in AGENT_REGISTRY.values()
    )


def classify_agent(message: str) -> str:
    """Returns an AGENT_REGISTRY key. Always returns a valid key."""
    try:
        model = ChatOpenAI(
            model=settings.chat_model, api_key=settings.openai_api_key, temperature=0
        )
        prompt = _ROUTER_PROMPT_TEMPLATE.format(
            agent_list=_agent_list_text(), default_key=DEFAULT_AGENT_KEY
        )
        response = model.invoke(
            [SystemMessage(content=prompt), HumanMessage(content=message)]
        )
        key = (response.content or "").strip().lower().strip('"')
        return key if key in AGENT_REGISTRY else DEFAULT_AGENT_KEY
    except Exception:  # noqa: BLE001 - routing must never break the chat
        return DEFAULT_AGENT_KEY
