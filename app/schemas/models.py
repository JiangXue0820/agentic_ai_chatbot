from pydantic import BaseModel, Field
from typing import Any, List, Optional, Dict


class AgentInvokeRequest(BaseModel):
    input: str
    session_id: str = "default"
    secure_mode: bool = False
    context: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    memory_keys: Optional[List[str]] = None

class ToolCall(BaseModel):
    name: str
    inputs: Dict[str, Any]
    outputs: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    type: str = "answer"  # "answer" or "clarification"
    answer: str = ""
    intents: List[dict] = Field(default_factory=list)
    steps: List[dict] = Field(default_factory=list)
    used_tools: List[dict] = Field(default_factory=list)
    citations: List[dict] = Field(default_factory=list)

    # Clarification fields
    message: Optional[str] = None
    options: Optional[List[str]] = None

    # 🔒 Security-related fields
    secure_mode: bool = False
    masked_input: Optional[str] = None

class MemoryWrite(BaseModel):
    namespace: str
    type: str = Field(pattern="^(short|long|vector)$")
    content: str
    ttl: int | None = None
    sensitivity: str | None = None

class GmailSummaryRequest(BaseModel):
    limit: int = 5
    filter: str | None = None

class WeatherRequest(BaseModel):
    city: str | None = None
    lat: float | None = None
    lon: float | None = None

class VDBQueryRequest(BaseModel):
    query: str
    top_k: int = 3

class VDBIngestRequest(BaseModel):
    items: list[dict]


class VDBDocument(BaseModel):
    doc_id: str
    filename: str
    uploaded_at: str


class VDBDocumentsResponse(BaseModel):
    documents: List[VDBDocument] = Field(default_factory=list)


class VDBIngestResponse(BaseModel):
    ok: bool = True
    doc_id: str
    filename: str
    uploaded_at: str
    chunks: int
    empty_pages: Optional[int] = None
