# =====================================================
# app/agent/planning.py
# Step Structure & ReAct Planning Logic
# =====================================================

from dataclasses import dataclass
from typing import Dict, Any, Literal, Optional


@dataclass
class Step:
    intent: str
    thought: str
    action: Optional[str]
    input: Dict[str, Any]
    observation: Optional[Dict]
    status: Literal["planned", "running", "succeeded", "failed", "finished"]
    error: Optional[str] = None
    decide_next: bool = True
    require_human_confirmation: bool = False
    clarification_prompt: Optional[str] = None
