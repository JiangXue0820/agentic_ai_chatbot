from pydantic import BaseModel, Field
from typing import Any, List, Optional

class AgentInvokeRequest(BaseModel):
    input: str
    session_id: str = "default"
    context: dict[str, Any] | None = None
    tools: list[str] | None = None
    memory_keys: list[str] | None = None

class ToolCall(BaseModel):
    name: str
    inputs: dict
    outputs: dict | None = None

class AgentResponse(BaseModel):
    type: str = "answer"  # "answer" or "clarification"
    answer: str = ""
    intents: List[dict] = Field(default_factory=list)
    steps: List[dict] = Field(default_factory=list)  # Changed from List[str] to List[dict]
    used_tools: List[dict] = Field(default_factory=list)  # Changed from List[ToolCall] to List[dict] for flexibility
    citations: List[dict] = Field(default_factory=list)
    message: Optional[str] = None  # For clarification type
    options: Optional[List[str]] = None  # For clarification type

class MemoryWrite(BaseModel):
    namespace: str
    type: str = Field(pattern="^(short|long|vector)$")
    content: str
    ttl: int | None = None
    sensitivity: str | None = None

class GmailSummaryRequest(BaseModel):
    limit: int = 5

class WeatherRequest(BaseModel):
    city: str | None = None
    lat: float | None = None
    lon: float | None = None

class VDBQueryRequest(BaseModel):
    query: str
    top_k: int = 3

class VDBIngestRequest(BaseModel):
    items: list[dict]
