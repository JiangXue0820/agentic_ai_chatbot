# Agentic AI API – Quick Start & Documentation

## Overview

Agentic AI ARTc delivers a FastAPI service for a reasoning agent with integrated memory, tool calling, and a Streamlit UI. Key capabilities include:

- Multi-layer memory (short-term buffer, session persistence via SQLite, long-term recall via Chroma vector store)
- Tool adapters for Gmail, Weather, Vector DB, and conversational memory
- Pluggable LLM support (mock, DeepSeek, Gemini, OpenAI)
- Streamlit UI for demos and admin workflows
- Strong auth & logging guardrails (Bearer token, PII masking, CORS control)

---

## Prerequisites

- Python 3.11+
- PowerShell (Windows) or Bash-compatible shell
- Optional: Chrome/Firefox for UI testing, Docker for containerized deployment

---

## Quick Start

```powershell
# 1. Clone and navigate
git clone https://github.com/JiangXue0820/agentic_ai_chatbot.git
cd agentic_ai_chatbot

# 2. Create & activate virtual environment (inside the repo)
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# On macOS/Linux: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy env.example .env               # or: cp env.example .env
# Edit .env with your API_TOKEN, LLM_PROVIDER, Gmail creds, etc.

# 5. (Optional) Ingest demo knowledge base
python -m scripts.ingest

# 6. Launch FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. Launch Streamlit UI in another terminal
$env:API_BASE = "http://127.0.0.1:8000"
$env:API_TOKEN = "changeme"
streamlit run ui/app.py

# Visit:
#   API docs: http://127.0.0.1:8000/docs
#   UI demo : http://localhost:8501
```

---

## Environment Configuration

`.env` (partial):

```
API_TOKEN=changeme
LLM_PROVIDER=mock          # mock | deepseek | gemini | openai
DEEPSEEK_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
WEATHER_API=open-meteo
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Additional notes:

- Weather: switch to `openweather` + `OPENWEATHER_API_KEY` if needed.
- Gmail: OAuth flow in `app/api/gmail.py` + `app/tools/gmail_oauth.py`.
- Vector DB: `chromadb` by default, automatic in-memory fallback.
- LLM: `app/llm/provider.py` selects provider based on `.env`.

---

## Running & Testing

### Health Check
```bash
curl http://127.0.0.1:8000/health
```

### Invoke Agent
```bash
curl -H "Authorization: Bearer changeme" \
     -X POST http://127.0.0.1:8000/agent/invoke \
     -H "Content-Type: application/json" \
     -d '{"input":"Summarize my last 5 emails"}'
```

### Tools
```bash
# Weather
curl -H "Authorization: Bearer changeme" \
     -X POST http://127.0.0.1:8000/tools/weather/current \
     -H "Content-Type: application/json" \
     -d '{"city":"Singapore"}'

# VDB ingest/query
curl -H "Authorization: Bearer changeme" \
     -X POST http://127.0.0.1:8000/tools/vdb/ingest \
     -F "file=@docs/demo.pdf"

curl -H "Authorization: Bearer changeme" \
     -X POST http://127.0.0.1:8000/tools/vdb/query \
     -H "Content-Type: application/json" \
     -d '{"query":"Explain federated learning","top_k":3}'
```

### Memory API
```bash
curl -H "Authorization: Bearer changeme" \
     -X POST http://127.0.0.1:8000/memory/write \
     -H "Content-Type: application/json" \
     -d '{"namespace":"demo","type":"short","content":"hello"}'

curl -H "Authorization: Bearer changeme" \
     http://127.0.0.1:8000/memory/read?namespace=demo&limit=5
```

### Automated Tests
```bash
pytest tests/ -v
```

---

## Project Structure

```
agentic_ai_artc/
├── app/
│   ├── main.py                # FastAPI entry point
│   ├── api/                   # REST routers (/agent, /tools, /memory, /admin, /auth)
│   ├── agent/                 # Agent core, memory wrapper, planning, toolkit
│   ├── tools/                 # Gmail, Weather, Vector DB adapters, Conversation memory
│   ├── memory/                # SQLite store, Vector store abstraction
│   ├── llm/                   # LLMProvider abstraction
│   ├── guardrails/            # Security guard for PII masking
│   ├── security/              # Bearer auth dependency
│   ├── schemas/               # Pydantic models
│   └── utils/                 # config, logging, file parsing, text splitter
├── ui/app.py                  # Streamlit dashboard
├── scripts/ingest.py          # Demo knowledge ingestion
├── storage/                   # SQLite DB & Chroma persistence
├── tests/                     # Pytest suites
├── requirements.txt
├── design_document.md         # Spec / instructions
├── design_report.md           # Architecture overview
└── README.md                  # This file
```

---

## Key Features

- **ReAct-style reasoning** with LLM-driven planning (`Agent._plan_and_execute`)
- **Unified Tool Registry** to introspect and invoke adapters dynamically
- **Session & Long-term Memory** with TTL pruning, namespace isolation, vector search filters
- **Gmail OAuth support** with token refresh management
- **Weather adapter** with built-in timeouts and optional geocoding
- **Vector DB ingestion/query** using Chroma persistent client or in-memory fallback
- **Security Guardrails**: inbound/outbound sanitization, PII masking, centralized auth
- **Streamlit UI** for login, tool demos, knowledge management

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `chromadb not found` | `pip install chromadb==0.5.5` (or let fallback handle) |
| `Module 'app' not found` | Ensure commands run from project root with venv activated |
| Weather timeouts | Check network; Open-Meteo has rate limits |
| Port 8000 busy | Use `uvicorn app.main:app --port 8001` |
| Gmail OAuth errors | Confirm Google credentials in `.env` and token storage path |

---

## Roadmap

1. **LLM streaming** (SSE/WebSocket)
2. **Full Gmail Inbox experience** with message body summarization
3. **Docker/Compose** for reproducible deployment
4. **Advanced RBAC** & multi-tenant isolation
5. **Audit logging / analytics dashboards**

---

## Support

For architecture deep dive, see `design_report.md`. To contribute or extend, open issues or feature requests in your tracking system of choice. This MVP is intended as a teaching/demo project—adapt freely for production needs.
