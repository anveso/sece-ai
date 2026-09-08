"""
The multi-agent registry: every specialist agent SECE AI can route a
message to. Adding a new agent means adding one AgentSpec here (and, if it
needs a genuinely different tool set, extending build_tools in tools.py) -
no changes needed to the router or the chat endpoint.
"""
from dataclasses import dataclass
from typing import Dict
from uuid import UUID

from langchain_openai import ChatOpenAI
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session

from ..config import settings
from .prompts import ADMIN_AGENT_PROMPT, FACULTY_STUDENT_PROMPT, RESEARCH_AGENT_PROMPT
from .tools import build_tools


@dataclass(frozen=True)
class AgentSpec:
    key: str
    name: str
    # Shown to users in the agent picker AND fed to the router's classifier
    # prompt, so keep it accurate to what the agent is actually good at.
    description: str
    system_prompt: str


DEFAULT_AGENT_KEY = "faculty_student_assistant"

AGENT_REGISTRY: Dict[str, AgentSpec] = {
    "faculty_student_assistant": AgentSpec(
        key="faculty_student_assistant",
        name="Faculty & Student Assistant",
        description=(
            "General institutional Q&A: syllabi, circulars, policies, "
            "timetables, and everyday academic/administrative questions."
        ),
        system_prompt=FACULTY_STUDENT_PROMPT,
    ),
    "research_agent": AgentSpec(
        key="research_agent",
        name="Research Agent",
        description=(
            "Research support: current developments, recent papers, "
            "conferences, and funding/grant calls - information best found "
            "on the open web rather than in uploaded documents."
        ),
        system_prompt=RESEARCH_AGENT_PROMPT,
    ),
    "admin_agent": AgentSpec(
        key="admin_agent",
        name="Admin Agent",
        description=(
            "Drafts administrative content - circulars, notices, memos, "
            "emails - grounded in institutional policy documents."
        ),
        system_prompt=ADMIN_AGENT_PROMPT,
    ),
}


def build_agent(agent_key: str, db: Session, user_id: UUID) -> CompiledGraph:
    spec = AGENT_REGISTRY.get(agent_key, AGENT_REGISTRY[DEFAULT_AGENT_KEY])

    model = ChatOpenAI(
        model=settings.chat_model,
        api_key=settings.openai_api_key,
        streaming=True,
        temperature=0.2,
    )
    tools = build_tools(db, user_id)

    # NOTE: this pinned langgraph version (0.2.x) takes the system prompt via
    # `state_modifier`, not `prompt` - that kwarg was renamed in later
    # langgraph releases. If you upgrade langgraph, check
    # `inspect.signature(create_react_agent)` and update accordingly.
    return create_react_agent(model, tools, state_modifier=spec.system_prompt)
