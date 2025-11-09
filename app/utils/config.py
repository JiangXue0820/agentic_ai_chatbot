import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional, List

# Load .env file explicitly
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# =====================================================
# Storage Configuration
# =====================================================

BASE_STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")

# --- Session Memory (SQLite-based) ---
SESSION_MEM_PATH: str = os.path.join(BASE_STORAGE_DIR, "memory/sessionMem/mvp.db")

# --- Long-Term Memory (VectorDB backend) ---
LONGTERM_BACKEND: str = "chroma"
LONGTERM_PATH: str = os.path.join(BASE_STORAGE_DIR, "memory/longtermMem")

# --- Knowledge Base (Documents / Embeddings) ---
KNOWLEDGE_BACKEND: str = "chroma"
KNOWLEDGE_PATH: str = os.path.join(BASE_STORAGE_DIR, "knowledgebase")

# --- Gmail OAuth token store ---
GMAIL_TOKEN_PATH: str = os.getenv(
    "GMAIL_TOKEN_PATH",
    os.path.join(BASE_STORAGE_DIR, "gmail", "token.json"),
)
GMAIL_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

# --- Create dirs automatically if missing ---
# Create directory for SESSION_MEM_PATH (it's a file path, so get parent dir)
os.makedirs(os.path.dirname(SESSION_MEM_PATH), exist_ok=True)
# Create directories for LONGTERM_PATH and KNOWLEDGE_PATH (they are directory paths)
os.makedirs(LONGTERM_PATH, exist_ok=True)
os.makedirs(KNOWLEDGE_PATH, exist_ok=True)
os.makedirs(os.path.dirname(GMAIL_TOKEN_PATH), exist_ok=True)

# =====================================================
# Other constants
# =====================================================
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "deepseek")
DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))

class Settings(BaseSettings):
    ADMIN_USERNAME: str = None
    ADMIN_PASSWORD: str = None
    API_TOKEN: Optional[str] = None
    CORS_ALLOW_ORIGINS: list[str] = ["*"]

    # Gmail OAuth (configure for real runs)
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GMAIL_TOKEN_PATH: str = GMAIL_TOKEN_PATH
    GMAIL_SCOPES: List[str] = GMAIL_SCOPES

    # Weather
    WEATHER_API: str = "open-meteo"  # or "openweather"
    OPENWEATHER_API_KEY: str | None = None

    # Storage Configuration (use module-level constants)
    STORAGE_DIR: str = BASE_STORAGE_DIR
    SESSION_MEM_PATH: str = SESSION_MEM_PATH
    LONGTERM_BACKEND: str = LONGTERM_BACKEND
    LONGTERM_PATH: str = LONGTERM_PATH
    KNOWLEDGE_BACKEND: str = KNOWLEDGE_BACKEND
    KNOWLEDGE_PATH: str = KNOWLEDGE_PATH

    # LLM Configuration
    LLM_PROVIDER: str = DEFAULT_LLM_PROVIDER  # Options: "mock", "deepseek", "gemini", "openai"
    DEFAULT_MODEL: str = DEFAULT_MODEL
    DEFAULT_TEMPERATURE: float = DEFAULT_TEMPERATURE
    
    # DeepSeek
    DEEPSEEK_API_KEY: str | None = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # Gemini
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"
        env_file_encoding = "utf-8"

settings = Settings()
