# Requirement Analysis – Agentic AI API with Memory & Integrations (MVP)

## 1. Goal & Scope
- Build a minimal yet end‑to‑end **agentic AI system** exposing a REST API, maintaining **cross‑session memory**, and integrating **Gmail**, **Weather**, and a **Vector DB** for knowledge retrieval.
- Provide a simple **web UI** (Streamlit/Gradio) to demonstrate capabilities.
- Include **source code** + **startup guide** and **simple test examples**.

## 2. Success Criteria
- REST endpoints for agent invocation, memory read/write, and tool calls return **structured JSON**.
- UI can run the 3 sample scenarios successfully.
- Optional security & privacy features available (masking + bearer auth).

## 3. Assumptions & Constraints
- MVP first; extensible design.
- Gmail requires OAuth for real data; mock allowed for local demo.
- Weather uses Open‑Meteo (no key) by default; OpenWeather as an alternative.
- Vector DB local (Chroma/FAISS) to simplify setup.
- LLM provider abstracted (mock in MVP). Embeddings may be mocked or swapped.
- Storage via SQLite (persistent) and optional Redis (ephemeral) — MVP uses SQLite only.

## 4. Actors
- **End user** via Web UI.
- **API integrator** calling REST endpoints.
- **Admin/Developer** configuring credentials and observing logs.

## 5. Functional Requirements (High‑Level)
1) **Agent API** – `/agent/invoke` accepts user input, decides tools, composes answer, returns structured JSON (answer/steps/citations/used_tools).
2) **Memory** – read/write cross‑session facts and short‑term context. Vector similarity search optional.
3) **Gmail** – read recent N emails (sender/subject/date/snippet) and summarize.
4) **Weather** – current temperature, humidity, condition by city or lat/lon.
5) **Vector DB** – ingest/query knowledge chunks; return top‑k with scores and metadata.
6) **Web UI** – chat‑like interface + one‑click demo buttons.
7) **Optional** – privacy filters (mask PII), bearer token auth.

## 6. Non‑Functional Requirements
- **Performance**: p95 < 2s excluding LLM latency; retries and timeouts for external calls.
- **Security**: no plaintext secrets in logs or DB; .env for secrets; CORS scoped.
- **Reliability**: graceful error messages; health endpoint.
- **Observability**: structured logs with masked PII; basic metrics (counts/latency).
- **Maintainability**: modular package layout; typed models (Pydantic).
- **Portability**: Python 3.11+, optional Dockerization.

## 7. Acceptance Tests (from prompt)
- **Gmail**: input "Summarize my last 5 emails" ⇒ concise summary + list of 5 mail meta.
- **Weather**: input "What’s the weather in Singapore?" ⇒ temp (°C), humidity (%), condition + observed time + source.
- **Vector DB**: input "Explain privacy‑preserving federated learning" ⇒ 1–3 relevant chunks with scores + short explanation.

---

# Software Requirements Specification (SRS)

## 1. Introduction
This SRS details functional and non‑functional requirements for the **Agentic AI API with Memory and External Integrations** MVP.

## 2. System Overview
- **Backend**: FastAPI exposing `/agent`, `/tools`, `/memory`.
- **UI**: Streamlit (or Gradio) single‑page interface.
- **Integrations**: Gmail (OAuth), Weather (Open‑Meteo/OpenWeather), Vector DB (Chroma/FAISS), optional Redis.

## 3. Functional Requirements
### 3.1 Agent API
- **Endpoint**: `POST /agent/invoke`
- **Request**: `{ input: string, context?: object, tools?: string[], memory_keys?: string[] }` 
- **Response**: `{ answer: string, steps: string[], citations: object[], used_tools: {name,inputs,outputs}[] }`
- **Behavior**: reads short‑term memory, selects tools, aggregates results, calls LLM for final answer, writes brief summary to memory.

### 3.2 Memory Service
- **Write**: `POST /memory/write` with `{ namespace, type: short|long|vector, content, ttl? }`
- **Read**: `GET /memory/read?namespace=...&limit=...`
- **Constraints**: PII masking on write/log; TTL honored; namespace isolation by user.

### 3.3 Gmail Tool
- **Endpoint**: `POST /tools/gmail/summary` with `{ limit }`
- **Output**: list of emails (`id, from, subject, date, snippet`) + agent summary (via `/agent/invoke`).
- **Auth**: OAuth 2.0; tokens stored securely.

### 3.4 Weather Tool
- **Endpoint**: `POST /tools/weather/current` with `{ city | lat, lon }`
- **Output**: `{ temperature, humidity, condition, source, observed_at }`

### 3.5 Vector DB Tool
- **Ingest**: `POST /tools/vdb/ingest` with list of `{ id, text, metadata }`
- **Query**: `POST /tools/vdb/query` with `{ query, top_k }` ⇒ `[{ chunk, score, doc_id, metadata }]`

### 3.6 Web UI
- Chat input + JSON result panel; quick‑test buttons for 3 sample prompts; optional token entry.

### 3.7 Security & Privacy (Optional but Recommended)
- **Auth**: Bearer token middleware; `401/403` on missing/invalid tokens.
- **Privacy**: Log filter masks emails/tokens/phones; configurable logging sinks.
- **CORS**: allowlist; HTTPS in deployment.

## 4. Data Model
- `memories(id, user_id, namespace, type, content, ttl, created_at)`
- `kb_chunks(id, doc_id, chunk_text, metadata)`
- (Optional) `users(id, email_hash, created_at)` and `sessions(id, user_id, last_active_at)`

## 5. Quality Attributes
- **Extensibility**: new tools via adapter interface; new memory backends.
- **Testability**: pytest with TestClient; mock adapters.
- **Observability**: structured, masked logs.

## 6. Constraints & Risks
- Gmail OAuth complexity; local callback and consent screen setup.
- External API quotas and transient failures.
- Embedding/LLM provider choice affecting latency & cost.

## 7. Acceptance Criteria
As listed in Section 7 of Requirement Analysis.

---

# System Architecture Design (SAD)

## 1. Architectural Overview
```
[Web UI (Streamlit/Gradio)]
          |
   (Bearer Token)
          v
     [FastAPI]
   ┌──────────────┬─────────────────┬───────────────────┐
   │  Agent Core  │   Memory Layer  │   Tools Adapters  │
   │  (Planner)   │ (Short/Long/VDB)│ (Gmail/Weather/VDB)
   └──────┬────────┴───────────┬────┴───────────────┐
          │                    │                    │
       [LLMProvider]     [SQLite/Redis]        [3rd‑party APIs]
```

## 2. Modules
- **Agent Core**: orchestrates tool selection, memory access, and response composition.
- **LLM Provider**: abstract chat/summarize/embed; replace stub with real LLM.
- **Memory Layer**: `SQLiteStore` for short/long memories; `VectorStore` for semantic search.
- **Tools**: `GmailAdapter`, `WeatherAdapter`, `VDBAdapter` with normalized I/O contracts.
- **Security**: Bearer auth middleware; privacy filter for logs.
- **UI**: Streamlit single page invoking `/agent/invoke` and tool endpoints.

## 3. Key Interfaces (REST)
- `POST /agent/invoke` → structured answer & trace.
- `POST /tools/gmail/summary` → recent emails list.
- `POST /tools/weather/current` → current conditions.
- `POST /tools/vdb/ingest`, `POST /tools/vdb/query` → KB ops.
- `POST /memory/write`, `GET /memory/read` → memory ops.

## 4. Sequence Flows
### 4.1 Weather
1. UI → `/agent/invoke` ("What’s the weather in Singapore?")
2. Agent → WeatherAdapter → Weather API
3. Agent → LLM (compose) → write short memory → UI

### 4.2 Gmail Summary
1. UI → `/agent/invoke` ("Summarize my last 5 emails")
2. Agent → GmailAdapter → Gmail API (list/get)
3. Agent → LLM summarize → write short memory → UI

### 4.3 Vector Retrieval
1. UI → `/agent/invoke`
2. Agent → VDBAdapter.query(top_k)
3. Agent → LLM compose with snippets → UI

## 5. Data & Storage
- SQLite DB file at `SQLITE_PATH` for memories and (optionally) KB chunks.
- Vector DB via Chroma (preferred) or in‑process fallback.
- Secrets from `.env`; no secrets in code or logs.

## 6. Security & Privacy
- Bearer token required for all POST/GET except `/health`.
- Mask PII (email, tokens) in logs; avoid storing raw OAuth tokens.
- CORS limited to UI origin in deployment.

## 7. Deployment & Ops
- Local dev: `uvicorn` + Streamlit.
- CI: run pytest; lint optional.
- Future: Dockerfile + docker‑compose (API + Streamlit + optional Redis/Chroma service).

## 8. Trade‑offs
- Mocked LLM/Gmail favors demo speed over realism — easily swappable.
- SQLite simplifies ops but limits concurrency — acceptable for MVP.
- Open‑Meteo chosen for zero‑key startup; can switch to OpenWeather for richer fields.

## 9. Future Enhancements
- Real tool‑calling LLM with JSON schema.
- OAuth token storage & refresh; per‑user multi‑tenant memories.
- SSE/WebSocket streaming; tracing (OpenTelemetry).
- RBAC/API keys; rate limiting; audit logs.



# Agentic AI MVP – Code Skeleton & Startup Guide

> Minimal, end‑to‑end implementation scaffold for: Agent API + Memory + Gmail + Weather + Vector DB + Web UI (Streamlit).

---

## 1) Project Tree (proposed)
```
.
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── agent.py
│   │   ├── memory.py
│   │   └── tools.py
│   ├── agent/
│   │   └── core.py
│   ├── llm/
│   │   └── provider.py
│   ├── memory/
│   │   ├── sqlite_store.py
│   │   └── vector_store.py
│   ├── tools/
│   │   ├── gmail.py
│   │   ├── weather.py
│   │   └── vdb.py
│   ├── schemas/
│   │   └── models.py
│   ├── security/
│   │   └── auth.py
│   └── utils/
│       ├── config.py
│       └── logging.py
├── ui/
│   └── app.py
├── scripts/
│   └── ingest.py
├── tests/
│   ├── test_agent.py
│   ├── test_tools_weather.py
│   ├── test_tools_gmail.py
│   └── test_vdb.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 2) Backend Code (FastAPI)

### `app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.agent import router as agent_router
from app.api.tools import router as tools_router
from app.api.memory import router as memory_router
from app.utils.config import settings
from app.utils.logging import configure_logging

configure_logging()

app = FastAPI(title="Agentic AI MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router, prefix="/agent", tags=["agent"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])
app.include_router(memory_router, prefix="/memory", tags=["memory"])

@app.get("/health")
def health():
    return {"status": "ok"}
```

### `app/utils/config.py`
```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    API_TOKEN: str = "changeme"
    CORS_ALLOW_ORIGINS: list[str] = ["*"]

    # Gmail OAuth (configure for real runs)
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # Weather
    WEATHER_API: str = "open-meteo"  # or "openweather"
    OPENWEATHER_API_KEY: str | None = None

    # Storage
    SQLITE_PATH: str = "./mvp.db"

    # Vector store
    VECTOR_BACKEND: str = "chroma"  # or "sklearn"

    class Config:
        env_file = ".env"

settings = Settings()
```

### `app/utils/logging.py`
```python
import logging, re

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)\.[A-Za-z]{2,}")
TOKEN_RE = re.compile(r"(Bearer\s+)?([A-Za-z0-9-_]{20,})")

class MaskPIIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = EMAIL_RE.sub(lambda m: f"{m.group(1)[:2]}***@***", record.msg)
            msg = TOKEN_RE.sub("***TOKEN***", msg)
            record.msg = msg
        return True

def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger()
    logger.addFilter(MaskPIIFilter())
```

### `app/security/auth.py`
```python
from fastapi import Header, HTTPException, status, Depends
from app.utils.config import settings

async def require_bearer(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != settings.API_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")
    return {"user_id": "demo"}
```

### `app/schemas/models.py`
```python
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
```

### `app/llm/provider.py`
```python
"""LLM abstraction. For MVP we implement a deterministic stub and leave hooks for real LLMs."""
from typing import List, Dict

class LLMProvider:
    def chat(self, messages: List[Dict]) -> str:
        # Minimal stub – echo last user content with a polite preface
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"(mocked-llm) {last_user}"

    def summarize(self, items: list[dict] | list[str], max_lines: int = 8) -> str:
        # Naive summarizer for MVP
        if isinstance(items, list) and items and isinstance(items[0], dict):
            subjects = [it.get("subject") or it.get("title") or str(it) for it in items][:max_lines]
            return "; ".join(subjects)
        texts = [str(x) for x in items][:max_lines]
        return "; ".join(texts)

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Lightweight hash-based pseudo-embedding for MVP (replace with real embeddings later)
        def fe(s: str):
            import random
            random.seed(hash(s) & 0xffffffff)
            return [random.random() for _ in range(64)]
        return [fe(t) for t in texts]
```

### `app/memory/sqlite_store.py`
```python
import sqlite3, time
from typing import Any
from app.utils.config import settings

class SQLiteStore:
    def __init__(self, path: str | None = None):
        self.path = path or settings.SQLITE_PATH
        self._init()

    def _init(self):
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, user_id TEXT, namespace TEXT, type TEXT, content TEXT, ttl INTEGER, created_at INTEGER)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS kb_chunks (id INTEGER PRIMARY KEY, doc_id TEXT, chunk_text TEXT, metadata TEXT)"
            )

    def write(self, user_id: str, namespace: str, mtype: str, content: str, ttl: int | None):
        now = int(time.time())
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO memories(user_id, namespace, type, content, ttl, created_at) VALUES(?,?,?,?,?,?)",
                (user_id, namespace, mtype, content, ttl or 0, now),
            )

    def read(self, user_id: str, namespace: str, limit: int = 10) -> list[dict]:
        now = int(time.time())
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute(
                "SELECT content, type, ttl, created_at FROM memories WHERE user_id=? AND namespace=? ORDER BY created_at DESC LIMIT ?",
                (user_id, namespace, limit),
            ).fetchall()
        def alive(r):
            ttl = r[2]
            created = r[3]
            return ttl == 0 or (created + ttl) > now
        return [
            {"content": r[0], "type": r[1], "ttl": r[2], "created_at": r[3]}
            for r in rows if alive(r)
        ]
```

### `app/memory/vector_store.py`
```python
"""Simple pluggable vector store: try Chroma; fallback to sklearn-TFIDF + cosine."""
from typing import List, Dict

try:
    import chromadb
    from chromadb.utils import embedding_functions
    _HAVE_CHROMA = True
except Exception:
    _HAVE_CHROMA = False

from math import sqrt

class VectorStore:
    def __init__(self, collection: str = "kb"):
        self.collection_name = collection
        if _HAVE_CHROMA:
            self.client = chromadb.Client()
            self.coll = self.client.get_or_create_collection(collection)
            self.embedder = embedding_functions.DefaultEmbeddingFunction()
        else:
            self.docs: list[str] = []
            self.meta: list[dict] = []

    def ingest(self, docs: List[Dict]):
        if _HAVE_CHROMA:
            texts = [d["text"] for d in docs]
            ids = [d.get("id") or str(i) for i, _ in enumerate(texts)]
            self.coll.add(ids=ids, documents=texts, metadatas=[d.get("metadata", {}) for d in docs])
        else:
            for d in docs:
                self.docs.append(d["text"])
                self.meta.append(d.get("metadata", {}))

    def query(self, query: str, top_k: int = 3):
        if _HAVE_CHROMA:
            res = self.coll.query(query_texts=[query], n_results=top_k)
            out = []
            for i in range(len(res["ids"][0])):
                out.append({
                    "chunk": res["documents"][0][i],
                    "score": 1 - res["distances"][0][i],
                    "doc_id": res["ids"][0][i],
                    "metadata": res["metadatas"][0][i],
                })
            return out
        else:
            # cosine on naive hash-embeddings
            def emb(s):
                import random
                random.seed(hash(s) & 0xffffffff)
                return [random.random() for _ in range(64)]
            q = emb(query)
            def cos(a,b):
                num = sum(x*y for x,y in zip(a,b))
                da = sqrt(sum(x*x for x in a)); db = sqrt(sum(x*x for x in b))
                return num / (da*db + 1e-9)
            scored = []
            for i, t in enumerate(self.docs):
                scored.append((i, cos(q, emb(t))))
            scored.sort(key=lambda x: x[1], reverse=True)
            out = []
            for i, s in scored[:top_k]:
                out.append({"chunk": self.docs[i], "score": float(s), "doc_id": str(i), "metadata": self.meta[i]})
            return out
```

### `app/tools/weather.py`
```python
import requests, time
from typing import Optional
from app.utils.config import settings

class WeatherAdapter:
    def current(self, city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> dict:
        if settings.WEATHER_API == "open-meteo":
            if city and (lat is None or lon is None):
                # simple geocode via Open-Meteo geocoding API
                g = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1}).json()
                if not g.get("results"):
                    raise ValueError("City not found")
                lat = g["results"][0]["latitude"]; lon = g["results"][0]["longitude"]
            assert lat is not None and lon is not None
            r = requests.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": lat, "longitude": lon, "current_weather": True, "hourly": "relativehumidity_2m"
            }).json()
            cur = r.get("current_weather", {})
            humidity = None
            try:
                # derive humidity from current hour if available
                humidity = r["hourly"]["relativehumidity_2m"][0]
            except Exception:
                pass
            return {
                "temperature": cur.get("temperature"),
                "humidity": humidity,
                "condition": cur.get("weathercode"),
                "source": "open-meteo",
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        else:
            key = settings.OPENWEATHER_API_KEY
            if not key:
                raise RuntimeError("OPENWEATHER_API_KEY missing")
            if city:
                r = requests.get("https://api.openweathermap.org/data/2.5/weather", params={"q": city, "appid": key, "units": "metric"}).json()
            else:
                r = requests.get("https://api.openweathermap.org/data/2.5/weather", params={"lat": lat, "lon": lon, "appid": key, "units": "metric"}).json()
            main = r.get("main", {})
            return {
                "temperature": main.get("temp"),
                "humidity": main.get("humidity"),
                "condition": r.get("weather", [{}])[0].get("main"),
                "source": "openweather",
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
```

### `app/tools/gmail.py`
```python
"""Gmail adapter – structure in place; replace stub with OAuth flow in real runs."""
from typing import List, Dict

class GmailAdapter:
    def list_recent(self, limit: int = 5) -> List[Dict]:
        # TODO: implement Google OAuth + Gmail API calls
        # For MVP demo without credentials, return mock data.
        out = []
        for i in range(limit):
            out.append({
                "id": f"demo-{i}",
                "from": "alice@example.com",
                "subject": f"Sample subject {i}",
                "date": "2025-11-05T10:00:00Z",
                "snippet": "This is a placeholder email snippet"
            })
        return out
```

### `app/tools/vdb.py`
```python
from app.memory.vector_store import VectorStore

class VDBAdapter:
    def __init__(self):
        self.store = VectorStore("kb")

    def ingest_texts(self, items: list[dict]):
        # items: [{"id":..., "text":..., "metadata":{...}}]
        self.store.ingest(items)

    def query(self, query: str, top_k: int = 3):
        return self.store.query(query, top_k)
```

### `app/agent/core.py`
```python
from typing import List, Dict
from app.llm.provider import LLMProvider
from app.tools.weather import WeatherAdapter
from app.tools.gmail import GmailAdapter
from app.tools.vdb import VDBAdapter
from app.memory.sqlite_store import SQLiteStore

class Agent:
    def __init__(self):
        self.llm = LLMProvider()
        self.weather = WeatherAdapter()
        self.gmail = GmailAdapter()
        self.vdb = VDBAdapter()
        self.mem = SQLiteStore()

    def handle(self, user_id: str, text: str, tools: List[str] | None = None, memory_keys: List[str] | None = None) -> Dict:
        tools = tools or ["gmail","weather","vdb"]
        steps, used, citations = [], [], []
        answer_parts = []

        t = text.lower()
        if "weather" in t and "weather" in tools:
            steps.append("weather.current")
            w = self.weather.current(city="Singapore" if "singapore" in t else None)
            used.append({"name":"weather","inputs":{"city": "Singapore" if "singapore" in t else None},"outputs":w})
            answer_parts.append(f"Weather: {w.get('temperature')}°C, humidity {w.get('humidity')}%, condition {w.get('condition')}")
            citations.append({"type":"weather","source": w.get("source"), "observed_at": w.get("observed_at")})

        if "email" in t or "gmail" in t:
            steps.append("gmail.list")
            emails = self.gmail.list_recent(limit=5)
            used.append({"name":"gmail","inputs":{"limit":5},"outputs":{"count":len(emails)}})
            summary = self.llm.summarize(emails)
            answer_parts.append(f"Emails summary: {summary}")
            citations.append({"type":"email","ids":[e["id"] for e in emails]})

        if "explain" in t or "vector" in t or "knowledge" in t:
            steps.append("vdb.query")
            res = self.vdb.query(text, top_k=3)
            used.append({"name":"vdb","inputs":{"top_k":3},"outputs":{"hits":len(res)}})
            snippet = "; ".join(ch.get("chunk")[:120] for ch in res)
            answer_parts.append(f"KB: {snippet}")
            for r in res:
                citations.append({"type":"kb","doc_id": r["doc_id"], "score": r["score"]})

        if not answer_parts:
            # default LLM echo
            out = self.llm.chat([
                {"role":"system","content":"You are a helpful agent."},
                {"role":"user","content": text}
            ])
            answer_parts.append(out)

        # write short memory
        self.mem.write(user_id, "session:default", "short", text, ttl=24*3600)

        return {
            "answer": " | ".join(answer_parts),
            "used_tools": used,
            "citations": citations,
            "steps": steps
        }
```

### `app/api/agent.py`
```python
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
```

### `app/api/tools.py`
```python
from fastapi import APIRouter, Depends
from app.security.auth import require_bearer
from app.tools.gmail import GmailAdapter
from app.tools.weather import WeatherAdapter
from app.tools.vdb import VDBAdapter

router = APIRouter()

_gmail = GmailAdapter()
_weather = WeatherAdapter()
_vdb = VDBAdapter()

@router.post("/gmail/summary")
async def gmail_summary(limit: int = 5, user=Depends(require_bearer)):
    emails = _gmail.list_recent(limit=limit)
    return {"emails": emails}

@router.post("/weather/current")
async def weather_current(city: str | None = None, lat: float | None = None, lon: float | None = None, user=Depends(require_bearer)):
    return _weather.current(city=city, lat=lat, lon=lon)

@router.post("/vdb/query")
async def vdb_query(query: str, top_k: int = 3, user=Depends(require_bearer)):
    return {"results": _vdb.query(query, top_k)}

@router.post("/vdb/ingest")
async def vdb_ingest(items: list[dict], user=Depends(require_bearer)):
    _vdb.ingest_texts(items)
    return {"ingested": len(items)}
```

### `app/api/memory.py`
```python
from fastapi import APIRouter, Depends
from app.security.auth import require_bearer
from app.schemas.models import MemoryWrite
from app.memory.sqlite_store import SQLiteStore

router = APIRouter()
store = SQLiteStore()

@router.post("/write")
async def write(m: MemoryWrite, user=Depends(require_bearer)):
    store.write(user_id=user["user_id"], namespace=m.namespace, mtype=m.type, content=m.content, ttl=m.ttl)
    return {"ok": True}

@router.get("/read")
async def read(namespace: str, limit: int = 10, user=Depends(require_bearer)):
    return {"items": store.read(user_id=user["user_id"], namespace=namespace, limit=limit)}
```

---

## 3) Web UI (Streamlit)

### `ui/app.py`
```python
import os, requests, streamlit as st

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
API_TOKEN = os.getenv("API_TOKEN", "changeme")

st.set_page_config(page_title="Agentic AI MVP", layout="centered")
st.title("Agentic AI – Demo UI")

headers = {"Authorization": f"Bearer {API_TOKEN}"}

with st.sidebar:
    st.text_input("API Base", API_BASE, key="api_base")
    st.text_input("Bearer Token", API_TOKEN, key="api_token")
    if st.button("Health Check"):
        r = requests.get(f"{st.session_state.api_base}/health")
        st.write(r.json())

prompt = st.text_input("Ask the agent", value="Summarize my last 5 emails")
if st.button("Send"):
    r = requests.post(f"{st.session_state.api_base}/agent/invoke", json={"input": prompt}, headers={"Authorization": f"Bearer {st.session_state.api_token}"})
    st.json(r.json())

st.subheader("Quick Tests")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Gmail: last 5"):
        r = requests.post(f"{st.session_state.api_base}/agent/invoke", json={"input": "Summarize my last 5 emails"}, headers={"Authorization": f"Bearer {st.session_state.api_token}"})
        st.json(r.json())
with col2:
    if st.button("Weather: Singapore"):
        r = requests.post(f"{st.session_state.api_base}/agent/invoke", json={"input": "What's the weather in Singapore?"}, headers={"Authorization": f"Bearer {st.session_state.api_token}"})
        st.json(r.json())
with col3:
    if st.button("VDB: PPFL"):
        r = requests.post(f"{st.session_state.api_base}/agent/invoke", json={"input": "Explain privacy-preserving federated learning"}, headers={"Authorization": f"Bearer {st.session_state.api_token}"})
        st.json(r.json())
```

---

## 4) Ingestion Script (KB)

### `scripts/ingest.py`
```python
import json, sys
from app.tools.vdb import VDBAdapter

if __name__ == "__main__":
    v = VDBAdapter()
    items = [
        {"id":"ppfl_1","text":"Privacy-preserving federated learning uses secure aggregation to protect client updates.","metadata":{"source":"demo"}},
        {"id":"ppfl_2","text":"Differential privacy can be applied to gradients in FL to bound leakage.","metadata":{"source":"demo"}},
        {"id":"ppfl_3","text":"Homomorphic encryption enables computation on encrypted data in FL settings.","metadata":{"source":"demo"}},
    ]
    v.ingest_texts(items)
    print(json.dumps({"ingested": len(items)}))
```

---

## 5) Tests (pytest)

### `tests/test_agent.py`
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

AUTH = {"Authorization": "Bearer changeme"}

def test_invoke_echo():
    r = client.post("/agent/invoke", json={"input":"hello"}, headers=AUTH)
    assert r.status_code == 200
    assert "answer" in r.json()
```

### `tests/test_tools_weather.py`
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer changeme"}

def test_weather_endpoint():
    r = client.post("/tools/weather/current", headers=AUTH, json={"city":"Singapore"})
    assert r.status_code == 200
    assert "temperature" in r.json()
```

### `tests/test_tools_gmail.py`
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer changeme"}

def test_gmail_mock():
    r = client.post("/tools/gmail/summary", headers=AUTH, json={"limit": 3})
    assert r.status_code == 200
    data = r.json()["emails"]
    assert len(data) == 3
```

### `tests/test_vdb.py`
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer changeme"}

def test_vdb_query():
    client.post("/tools/vdb/ingest", headers=AUTH, json=[{"id":"d1","text":"federated learning uses secure aggregation","metadata":{}}])
    r = client.post("/tools/vdb/query", headers=AUTH, json={"query":"Explain secure aggregation"})
    assert r.status_code == 200
    assert "results" in r.json()
```

---

## 6) Requirements & Env

### `requirements.txt`
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
requests==2.32.3
python-dotenv==1.0.1
loguru==0.7.2
streamlit==1.39.0
# Vector store options (one is enough for MVP)
chromadb==0.5.5
# google api (enable when wiring real Gmail)
google-api-python-client==2.149.0
google-auth==2.35.0
google-auth-oauthlib==1.2.1
pytest==8.3.3
```

### `.env.example`
```
API_TOKEN=changeme
CORS_ALLOW_ORIGINS=["*"]
# Weather
WEATHER_API=open-meteo
OPENWEATHER_API_KEY=
# Gmail
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
# Storage
SQLITE_PATH=./mvp.db
VECTOR_BACKEND=chroma
```

---

## 7) README (Startup Guide)

### Prereqs
- Python 3.11+
- (Optional) Docker if you want containerized run

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### (Optional) Ingest demo KB
```bash
python -m scripts.ingest
```

### Run backend
```bash
uvicorn app.main:app --reload --port 8000
```

### Run UI (Streamlit)
```bash
export API_BASE=http://127.0.0.1:8000
export API_TOKEN=changeme
streamlit run ui/app.py
```

Open http://localhost:8501 and try the three demo buttons.

### Simple cURL tests
```bash
curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/agent/invoke -H 'Content-Type: application/json' -d '{"input":"Summarize my last 5 emails"}'

curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/tools/weather/current -H 'Content-Type: application/json' -d '{"city":"Singapore"}'

curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/tools/vdb/ingest -H 'Content-Type: application/json' -d '[{"id":"d1","text":"privacy-preserving federated learning via secure aggregation","metadata":{"source":"demo"}}]'

curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/tools/vdb/query -H 'Content-Type: application/json' -d '{"query":"Explain privacy-preserving federated learning"}'
```

### Notes
- Gmail adapter is mocked until OAuth is configured. Replace `gmail.py` with real calls (users.messages.list/get) once credentials are ready.
- Weather uses Open‑Meteo by default (no key). Switch to OpenWeather by setting `WEATHER_API=openweather` and provide `OPENWEATHER_API_KEY`.
- Vector store prefers Chroma; if unavailable, the fallback hash‑embedding will still demo behavior.

---

## 8) Next Steps (to productionize)
- Replace LLM stub with real provider + tool‑calling schema.
- Implement Gmail OAuth flow and secure token storage.
- Add SSE/WebSocket for streaming responses.
- Dockerize (Dockerfile + docker-compose.yml with Redis, if desired).
- Expand privacy filters (PII regex library) and add structured audit logs.
- Add basic UI auth and session‑scoped memories.

