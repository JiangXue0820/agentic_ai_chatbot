from fastapi import APIRouter, Depends, HTTPException
from app.security.auth import require_bearer
from app.schemas.models import AgentInvokeRequest, AgentResponse
from app.agent.core import Agent
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
agent = Agent()

@router.post("/invoke", response_model=AgentResponse)
async def invoke(req: AgentInvokeRequest, user=Depends(require_bearer)):
    """
    Invoke the agent with a user query.
    
    Args:
        req: Request containing user input and optional session_id
        user: Authenticated user from bearer token
        
    Returns:
        AgentResponse with answer, steps, tools used, and citations
        
    Raises:
        HTTPException: If agent processing fails
    """
    try:
        logger.info(f"Agent invoke - user: {user['user_id']}, session: {req.session_id}, input: {req.input[:100]}")
        
        # Call agent with correct parameters
        res = agent.handle(
            user_id=user["user_id"],
            text=req.input,
            session_id=req.session_id
        )
        
        logger.info(f"Agent response type: {res.get('type')}")
        return res
        
    except Exception as e:
        logger.error(f"Agent invoke error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent processing failed: {str(e)}"
        )
