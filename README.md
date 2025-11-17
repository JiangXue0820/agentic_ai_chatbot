# Agentic AI API – Quick Start & Documentation

## Overview

Agentic AI Chatbot is a multi-turn FastAPI service that combines reasoning, memory, and tooling in a single agent workflow. It offers:

- **Agent-first architecture** with LLM-driven ReAct planning, `PlanTrace` auditing, and clarification fallbacks.
- **Layered memory stack** that blends short-term RAM, SQLite session state, and Chroma long-term recall with strict user/session scoping.
- **Unified ToolRegistry** powering Gmail (OAuth), weather, vector-DB search, and conversation-recall adapters through a single invoke interface.
- **Pluggable LLM providers** (mock, DeepSeek, Gemini, OpenAI) selected via configuration without code changes.
- **Security guardrails** spanning bearer-token authentication, content sanitization, and logging.
- **Streamlit UI** wired to `/auth`, `/agent`, `/tools`, and `/admin` endpoints for rapid testing and demo flows

---

## Project Structure

```
agentic_ai_chatbot/
├── app/
│   ├── main.py                 # FastAPI application entry (router setup)
│   ├── api/                    # REST routes
│   │   ├── agent.py            # /agent/invoke endpoint
│   │   ├── tools.py            # /tools/...
│   │   ├── memory.py           # /memory/...
│   │   ├── admin.py            # /admin/bootstrap, reset
│   │   └── auth.py             # /auth/login
│   ├── agent/                  # Agent internals & ReAct orchestration
│   │   ├── core.py             # Agent main class
│   │   ├── memory.py           # Memory store wrappers
│   │   ├── planning.py         # Step, PlanTrace
│   │   ├── intent.py           # Intent recognition
│   │   └── toolkit.py          # ToolRegistry
│   ├── tools/                  # External tool adapters (Gmail, Weather, VDB, Memory)
│   ├── memory/                 # SQLite & VectorStore implementations
│   ├── llm/                    # LLMProvider abstraction
│   ├── security/               # Token validation helpers
│   ├── guardrails/             # Inbound/outbound safety filters
│   ├── schemas/                # Pydantic models
│   └── utils/                  # Config, logging, file parsing, text splitting
├── ui/                         # Streamlit frontend
├── scripts/                    # Data ingestion scripts
├── storage/                    # SQLite DBs & Chroma persistence
├── tests/                      # Pytest coverage
├── README.md
└── design_report.md
```

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

# 5. (Optional) Setup gmail authorization
# Follow the insturction below "Environment Configuration → Gmail OAuth Setup Steps
python scripts/setup_gmail_oauth.py

# 6. Launch FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 7. Launch Streamlit UI in another terminal
export API_BASE="http://127.0.0.1:8000"
export API_TOKEN="my_token"   ### change the token 
streamlit run ui/app.py

```

---

## Environment Configuration

`.env` (partial):

```
API_TOKEN=changeme         # needs to be changed to your secrete key
LLM_PROVIDER=mock          # mock | deepseek | gemini | openai
DEEPSEEK_API_KEY=          # the API key of the chosen LLM_PROVIDER should be provided
GEMINI_API_KEY=
OPENAI_API_KEY=
WEATHER_API=open-meteo
GOOGLE_CLIENT_ID=          # Check Gmail OAuth Setup Steps in below to get the ID and Secrete
GOOGLE_CLIENT_SECRET=
```

### Additional notes:

#### Weather

Switch to `openweather` + `OPENWEATHER_API_KEY` if needed.

#### LLM

Select **one** of the LLM provider in `.env`, and config with correct api token, then `app/llm/provider.py` will use the chosen one.

#### Gmail OAuth Setup Steps

1. **Get OAuth Credentials in Google Cloud Console**
* Go to [Google Cloud Console](https://console.cloud.google.com/)
* Create a project (or select an existing one)
* Enable Gmail API:
   - Go to "APIs & Services" → "Library"
   - Search for "Gmail API" and enable it
* Create OAuth 2.0 Client ID:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID" (For the first time, you need to "Configure consent screen")
   - Application type: "Web application"
   - Add authorized redirect URI: http://127.0.0.1:8000/gmail/oauth/callback
   - Click "Create"; Save and copy the Client ID and Client Secret in .env
```bash
# .env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

2. **Start the API Server**
Make sure the server is running:
```bash
uvicorn app.main:app --reload
```
The server should be running at http://127.0.0.1:8000

3. **Run the OAuth Setup Script**
Open another terminal, and run the following script: 
```bash
python scripts/setup_gmail_oauth.py
```
Example script output:
```bash
1. Checking server...
   ✓ Server is running
2. Checking authorization status...
   ⚠ Not authorized yet
3. Getting authorization URL...
   ✓ URL generated
4. Opening browser...
   # The browser will automatically opened, and you need to select the correct account and consent
   ✓ Browser opened   
5. After authorizing in browser, paste the callback URL or code:
   > http://127.0.0.1:8000/xxxxxxxxx/gmail.readonly
6. Completing authorization...
   ✓ Authorization complete!

✅ Gmail OAuth setup successful! You can now use Gmail features.
```
After the authorization step is done, you will find a new file in `.\storage\gmail\token.json`

4. **Verify Setup**
After setup, the access token will be saved in storage/gmail/token.json. You can verify by:
```bash
curl http://127.0.0.1:8000/gmail/oauth/status
```
You will see `{"authorized":true}` if the system is setup correctly. 

5. **Additional Notes**
* The redirect URI must exactly match what's configured in Google Console, which is http://127.0.0.1:8000/gmail/oauth/callback in this project
* When running `python scripts/setup_gmail_oauth.py`, if the authorization is blocked, saying the account is not finished verify:
   - Go to "APIs & Services" → "Credentials"
   - Select the OAuth 2.0 Client IDs and enter
   - Go to "Audience"  → For Test users, click "Add users" and input the gmail account


## Running & Testing

### Health Check
```bash
curl http://127.0.0.1:8000/health
```

### Streamlit UI

For the best experience, use the Streamlit UI:
```bash
streamlit run ui/app.py
```

Visit http://localhost:8501 for a friendly chat interface.

### Automated Tests
```bash
pytest tests/ -v
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

## Support

For architecture deep dive, see `design_report.md`. 