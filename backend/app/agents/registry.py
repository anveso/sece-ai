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
from .prompts import (
    ADMIN_AGENT_PROMPT,
    FACULTY_RESEARCH_PERFORMANCE_AGENT_PROMPT,
    FACULTY_STUDENT_PROMPT,
    FUNDING_OPPORTUNITY_AGENT_PROMPT,
    PATENT_INNOVATION_AGENT_PROMPT,
    PHD_SCHOLAR_MONITORING_AGENT_PROMPT,
    PUBLICATION_INTELLIGENCE_AGENT_PROMPT,
    RESEARCH_AGENT_PROMPT,
    RESEARCH_DASHBOARD_MANAGEMENT_AGENT_PROMPT,
    RESEARCH_ETHICS_COMPLIANCE_AGENT_PROMPT,
    RESEARCH_SUPER_AGENT_PROMPT,
)
from .tools import build_tools


@dataclass(frozen=True)
class AgentSpec:
    key: str
    name: str
    # Shown to users in the agent picker AND fed to the router's classifier
    # prompt, so keep it accurate to what the agent is actually good at.
    description: str
    system_prompt: str
    # Groups the agent picker UI into sections (frontend/components/
    # ChatWindow.tsx renders one <optgroup> per distinct value here) and has
    # no effect on routing/behavior.
    group: str = "General"


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
        group="General",
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
        group="General",
    ),
    "admin_agent": AgentSpec(
        key="admin_agent",
        name="Admin Agent",
        description=(
            "Drafts administrative content - circulars, notices, memos, "
            "emails - grounded in institutional policy documents."
        ),
        system_prompt=ADMIN_AGENT_PROMPT,
        group="General",
    ),
    # --- Institutional Research Agentic AI Structure (Phase 1) ---
    "research_super_agent": AgentSpec(
        key="research_super_agent",
        name="Research Super Agent",
        description=(
            "Institutional research overview and front desk: points you to "
            "the right research specialist, or gives a synthesized strategic "
            "answer directly for broad research questions."
        ),
        system_prompt=RESEARCH_SUPER_AGENT_PROMPT,
        group="Research Command Centre",
    ),
    "funding_opportunity_agent": AgentSpec(
        key="funding_opportunity_agent",
        name="Funding Opportunity & Proposal Agent",
        description=(
            "Finds funding/grant calls (DST, SERB, AICTE, industry, "
            "international) and helps draft proposals."
        ),
        system_prompt=FUNDING_OPPORTUNITY_AGENT_PROMPT,
        group="Research Command Centre",
    ),
    "publication_intelligence_agent": AgentSpec(
        key="publication_intelligence_agent",
        name="Publication Intelligence Agent",
        description=(
            "Journal/conference selection, indexing and quality checks "
            "(Scopus, UGC-CARE, predatory-journal warnings), citation help."
        ),
        system_prompt=PUBLICATION_INTELLIGENCE_AGENT_PROMPT,
        group="Research Command Centre",
    ),
    "patent_innovation_agent": AgentSpec(
        key="patent_innovation_agent",
        name="Patent & Innovation Agent",
        description=(
            "Patent filing guidance, prior-art search, IP process, and "
            "connecting work to SECE's innovation/startup initiatives."
        ),
        system_prompt=PATENT_INNOVATION_AGENT_PROMPT,
        group="Research Command Centre",
    ),
    "phd_scholar_monitoring_agent": AgentSpec(
        key="phd_scholar_monitoring_agent",
        name="Ph.D. Scholar Monitoring Agent",
        description=(
            "Tracks a scholar's doctoral progress (RAC meetings, "
            "milestones, thesis timeline) from uploaded records."
        ),
        system_prompt=PHD_SCHOLAR_MONITORING_AGENT_PROMPT,
        group="Research Command Centre",
    ),
    "research_ethics_compliance_agent": AgentSpec(
        key="research_ethics_compliance_agent",
        name="Research Ethics & Compliance Agent",
        description=(
            "Ethics/IRB approval process, plagiarism and research-integrity "
            "policy, informed consent, compliance questions."
        ),
        system_prompt=RESEARCH_ETHICS_COMPLIANCE_AGENT_PROMPT,
        group="Research Command Centre",
    ),
    "faculty_research_performance_agent": AgentSpec(
        key="faculty_research_performance_agent",
        name="Faculty Research Performance Agent",
        description=(
            "Helps one faculty member organize their own research output "
            "for appraisals, API/KRA scoring, or promotion cases."
        ),
        system_prompt=FACULTY_RESEARCH_PERFORMANCE_AGENT_PROMPT,
        group="Research Command Centre",
    ),
    "research_dashboard_management_agent": AgentSpec(
        key="research_dashboard_management_agent",
        name="Research Dashboard & Management Agent",
        description=(
            "Consolidated status summary across funding, publications, "
            "patents, scholars, ethics, and faculty performance."
        ),
        system_prompt=RESEARCH_DASHBOARD_MANAGEMENT_AGENT_PROMPT,
        group="Research Command Centre",
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
