"""Lists the specialist agents available for the conversation agent picker."""
from fastapi import APIRouter, Depends

from ..agents.registry import AGENT_REGISTRY
from ..auth import get_current_user
from ..models import User
from ..schemas import AgentOut

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
def list_agents(current_user: User = Depends(get_current_user)):
    auto = AgentOut(
        key="auto",
        name="Auto",
        description="Automatically route each message to the best specialist agent.",
    )
    return [auto] + [
        AgentOut(key=s.key, name=s.name, description=s.description)
        for s in AGENT_REGISTRY.values()
    ]
