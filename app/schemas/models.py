from pydantic import BaseModel, Field
from typing import Any, List, Optional

class AgentInvokeRequest(BaseModel):
    input: str
    context: dict[str, Any] | None = None
    tools: list[str] | None = None
    memory_keys: list[str] | None = None

class ToolCall(BaseModel):
    name: str
    inputs: dict
    outputs: dict | None = None

class AgentResponse(BaseModel):
    answer: str
    used_tools: List[ToolCall] = Field(default_factory=list)
    citations: List[dict] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)

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
