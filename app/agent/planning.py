# =====================================================
# app/agent/planning.py
# Step and PlanTrace data models for reasoning trace
# =====================================================

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


@dataclass
class Step:
    """Represents a single reasoning or action step in the ReAct loop."""
    intent: str
    thought: str
    action: Optional[str] = None
    input: Dict[str, Any] = field(default_factory=dict)
    observation: Optional[Any] = None
    status: str = "planned"  # planned | running | succeeded | failed | finished
    decide_next: bool = True
    error: Optional[str] = None
    memory_used: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def is_finished(self) -> bool:
        """Return True if this step ends the reasoning process."""
        return self.status in ("finished", "failed") or not self.decide_next


class PlanTrace:
    """Tracks the full execution trace of an agent reasoning session."""
    def __init__(self, user_query: str):
        self.user_query = user_query
        self.steps: List[Step] = []
        self.created_at = datetime.utcnow().isoformat()

    def add_step(self, step: Step):
        """Append a new reasoning step to the trace."""
        self.steps.append(step)

    def summarize(self) -> str:
        """Human-readable summary of reasoning steps."""
        summary_lines = [f"Plan Trace for: {self.user_query}"]
        for i, s in enumerate(self.steps, 1):
            obs_preview = ""
            if s.observation:
                if isinstance(s.observation, dict):
                    obs_preview = json.dumps(s.observation, ensure_ascii=False)[:80]
                else:
                    obs_preview = str(s.observation)[:80]
            memory_note = " | 🧠 used memory" if getattr(s, "memory_used", False) else ""
            summary_lines.append(
                f"Step {i}: [{s.status.upper()}] {s.intent} → {s.action or 'None'} | "
                f"Thought: {s.thought[:60]} | Obs: {obs_preview}{memory_note}"
            )
        return "\n".join(summary_lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the trace to JSON-compatible dictionary."""
        return {
            "user_query": self.user_query,
            "created_at": self.created_at,
            "steps": [asdict(s) for s in self.steps],
        }

    def clear(self):
        """Reset the trace."""
        self.steps.clear()
