from fastapi import APIRouter, Depends
from app.security.auth import require_bearer
from app.schemas.models import AgentInvokeRequest, AgentResponse
from app.agent.core import Agent

router = APIRouter()
agent = Agent()

@router.post("/invoke", response_model=AgentResponse)
async def invoke(req: AgentInvokeRequest, user=Depends(require_bearer)):
    res = agent.handle(user_id=user["user_id"], text=req.input, tools=req.tools, memory_keys=req.memory_keys)
    return res
