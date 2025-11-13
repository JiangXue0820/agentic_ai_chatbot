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
        req: Request containing user input, session_id, and optional secure_mode
        user: Authenticated user (from bearer token)
    Returns:
        AgentResponse with structured fields (answer, steps, used_tools, etc.)
    Raises:
        HTTPException: If agent processing fails
    """
    try:
        logger.info(
            f"[AgentInvoke] user={user['user_id']} "
            f"session={req.session_id} secure_mode={req.secure_mode} "
            f"input={req.input[:100]}"
        )

        # === Call core agent logic ===
        result = agent.handle(
            user_id=user["user_id"],
            text=req.input,
            session_id=req.session_id,
            secure_mode=req.secure_mode,
        )

        # === Normalize response to fit AgentResponse schema ===
        if not isinstance(result, dict):
            logger.warning("Agent returned non-dict result; coercing to dict")
            result = {"answer": str(result)}

        response_data = {
            "type": result.get("type", "answer"),
            "answer": result.get("answer", ""),
            "intents": result.get("intents", []),
            "steps": result.get("steps", []),
            "used_tools": result.get("used_tools", []),
            "citations": result.get("citations", []),
            "message": result.get("message"),
            "options": result.get("options"),
            "secure_mode": result.get("secure_mode", req.secure_mode),
            "masked_input": result.get("masked_input"),
        }

        response = AgentResponse(**response_data)

        logger.info(
            f"[AgentResponse] type={response.type} secure={response.secure_mode} "
            f"masked_input={'yes' if response.masked_input else 'no'}"
        )

        return response

    except Exception as e:
        logger.error(f"[AgentInvoke] error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent processing failed: {str(e)}",
        )
