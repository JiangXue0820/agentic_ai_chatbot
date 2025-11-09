# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.agent import router as agent_router
from app.api.tools import router as tools_router
from app.api.memory import router as memory_router
from app.api.auth import router as auth_router  # 新增
from app.api.gmail import router as gmail_router
from app.utils.config import settings
from app.utils.logging import configure_logging

configure_logging()

app = FastAPI(title="Agentic AI MVP", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Register Routes ===
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(gmail_router, prefix="/gmail", tags=["gmail"])
app.include_router(agent_router, prefix="/agent", tags=["agent"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])
app.include_router(memory_router, prefix="/memory", tags=["memory"])

@app.get("/health")
def health():
    return {"status": "ok"}
