# Agentic AI MVP – Project Documentation

> Minimal, end-to-end implementation scaffold for: Agent API + Memory + Gmail + Weather + Vector DB + Web UI (Streamlit).

---

## Project Overview

This is an **Agentic AI system** exposing a REST API with:
- **Cross-session memory** (SQLite + Vector DB)
- **Gmail integration** (OAuth ready, currently mocked)
- **Weather API** (Open-Meteo by default)
- **Vector Database** (Chroma/FAISS for knowledge retrieval)
- **Web UI** (Streamlit demo interface)

---

## Prerequisites

- Python 3.11+
- (Optional) Docker if you want containerized run

---

## Setup

### 1. Clone and Navigate
```bash
cd agentic_ai_artc
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` to customize settings (optional for MVP demo):
- `API_TOKEN`: Bearer token for API authentication
- `WEATHER_API`: Choose between "open-meteo" (default, no key) or "openweather"
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: For real Gmail integration

---

## Running the Application

### 1. (Optional) Ingest Demo Knowledge Base
```bash
python -m scripts.ingest
```

This will load sample data about privacy-preserving federated learning into the vector database.

### 2. Run Backend API
```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`

Check health: `http://127.0.0.1:8000/health`

### 3. Run Web UI (Streamlit)

In a new terminal:
```bash
# Windows (PowerShell)
$env:API_BASE="http://127.0.0.1:8000"
$env:API_TOKEN="changeme"
streamlit run ui/app.py

# Linux/Mac
export API_BASE=http://127.0.0.1:8000
export API_TOKEN=changeme
streamlit run ui/app.py
```

Open `http://localhost:8501` in your browser.

---

## Testing the System

### Web UI Quick Tests

The UI provides three quick-test buttons:

1. **Gmail: last 5** - Summarizes last 5 emails (currently returns mock data)
2. **Weather: Singapore** - Gets current weather for Singapore
3. **VDB: PPFL** - Queries vector DB about privacy-preserving federated learning

### Manual API Testing with cURL

#### 1. Test Agent Invocation (Email Summary)
```bash
curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/agent/invoke -H 'Content-Type: application/json' -d '{"input":"Summarize my last 5 emails"}'
```

#### 2. Test Weather Tool
```bash
curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/tools/weather/current -H 'Content-Type: application/json' -d '{"city":"Singapore"}'
```

#### 3. Test Vector DB Ingestion
```bash
curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/tools/vdb/ingest -H 'Content-Type: application/json' -d '{"items":[{"id":"d1","text":"privacy-preserving federated learning via secure aggregation","metadata":{"source":"demo"}}]}'
```

#### 4. Test Vector DB Query
```bash
curl -H "Authorization: Bearer changeme" -X POST http://127.0.0.1:8000/tools/vdb/query -H 'Content-Type: application/json' -d '{"query":"Explain privacy-preserving federated learning","top_k":3}'
```

### Automated Tests

Run the test suite:
```bash
pytest tests/ -v
```

---

## API Endpoints

### Agent
- `POST /agent/invoke` - Main agent endpoint
  - Request: `{"input": "your question", "tools": ["gmail","weather","vdb"], "memory_keys": []}`
  - Response: `{"answer": "...", "used_tools": [...], "citations": [...], "steps": [...]}`

### Tools
- `POST /tools/gmail/summary` - Get recent emails (limit parameter)
- `POST /tools/weather/current` - Get weather (city or lat/lon)
- `POST /tools/vdb/ingest` - Ingest knowledge chunks
- `POST /tools/vdb/query` - Query knowledge base (query, top_k)

### Memory
- `POST /memory/write` - Write to memory
  - Request: `{"namespace": "...", "type": "short|long|vector", "content": "...", "ttl": 86400}`
- `GET /memory/read` - Read from memory
  - Params: `namespace`, `limit`

### Health
- `GET /health` - Health check endpoint

---

## Project Structure

```
agentic_ai_artc/
├── app/
│   ├── main.py                  # FastAPI application entry
│   ├── api/
│   │   ├── agent.py            # Agent invocation endpoint
│   │   ├── memory.py           # Memory read/write endpoints
│   │   └── tools.py            # Tool endpoints (Gmail, Weather, VDB)
│   ├── agent/
│   │   └── core.py             # Agent orchestration logic
│   ├── llm/
│   │   └── provider.py         # LLM abstraction (currently mocked)
│   ├── memory/
│   │   ├── sqlite_store.py     # SQLite memory storage
│   │   └── vector_store.py     # Vector DB (Chroma/fallback)
│   ├── tools/
│   │   ├── gmail.py            # Gmail adapter (currently mocked)
│   │   ├── weather.py          # Weather API adapter
│   │   └── vdb.py              # Vector DB adapter
│   ├── schemas/
│   │   └── models.py           # Pydantic models
│   ├── security/
│   │   └── auth.py             # Bearer token authentication
│   └── utils/
│       ├── config.py           # Configuration settings
│       └── logging.py          # PII-masked logging
├── ui/
│   └── app.py                  # Streamlit web interface
├── scripts/
│   └── ingest.py               # Knowledge base ingestion script
├── tests/
│   ├── test_agent.py
│   ├── test_tools_weather.py
│   ├── test_tools_gmail.py
│   └── test_vdb.py
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

---

## Configuration Notes

### Weather API
- **Default**: Open-Meteo (no API key required)
- **Alternative**: OpenWeather (set `WEATHER_API=openweather` and provide `OPENWEATHER_API_KEY` in `.env`)

### Gmail Integration
- **Current**: Mock data for demo purposes
- **Production**: Implement OAuth 2.0 flow with Google credentials
  - Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`
  - Replace mock implementation in `app/tools/gmail.py`

### Vector Database
- **Preferred**: Chroma (install: `pip install chromadb`)
- **Fallback**: Hash-based pseudo-embeddings (if Chroma unavailable)

### LLM Provider
- **Current**: Mock echo implementation
- **Production**: Replace `app/llm/provider.py` with real LLM (OpenAI, Anthropic, etc.)

---

## Security Features

1. **Bearer Token Authentication**: All endpoints (except `/health`) require valid bearer token
2. **PII Masking**: Email addresses and tokens automatically masked in logs
3. **CORS**: Configurable allowed origins
4. **Secrets Management**: All sensitive data stored in `.env` file (not committed to git)

---

## Next Steps (Production Roadmap)

1. **LLM Integration**: Replace stub with real LLM provider (OpenAI, Claude, etc.)
2. **Gmail OAuth**: Implement full OAuth 2.0 flow with token refresh
3. **Streaming**: Add SSE/WebSocket for real-time response streaming
4. **Dockerization**: Add Dockerfile and docker-compose.yml
5. **Enhanced Privacy**: Expand PII detection and add audit logging
6. **Multi-tenancy**: Add user management and session-scoped memories
7. **Rate Limiting**: Implement API rate limits
8. **RBAC**: Add role-based access control

---

## Troubleshooting

### Issue: "chromadb not found"
**Solution**: Install chromadb: `pip install chromadb==0.5.5`  
(The system will automatically fall back to hash-based embeddings if unavailable)

### Issue: "Module 'app' not found"
**Solution**: Run commands from project root directory and ensure virtual environment is activated

### Issue: Weather API timeout
**Solution**: Check internet connection; Open-Meteo is rate-limited for high-frequency requests

### Issue: Port 8000 already in use
**Solution**: Use different port: `uvicorn app.main:app --port 8001`

---

## License

This is an MVP demonstration project. Adapt as needed for your use case.

---

## Support

For issues or questions, please refer to the design document (`design_doc.md`) for detailed architecture and requirements.

#   a g e n t i c _ a i _ c h a t b o t  
 