import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file explicitly
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    API_TOKEN: str = "changeme"
    CORS_ALLOW_ORIGINS: list[str] = ["*"]

    # Gmail OAuth (configure for real runs)
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # Weather
    WEATHER_API: str = "open-meteo"  # or "openweather"
    OPENWEATHER_API_KEY: str | None = None

    # Storage Configuration
    STORAGE_DIR: str = "./storage"
    
    # SQLite Storage
    SQLITE_PATH: str = "./storage/memory/mvp.db"
    
    # Vector Store
    VECTOR_BACKEND: str = "chroma"  # or "sklearn"
    CHROMA_PATH: str = "./storage/vectordb"

    # LLM Configuration
    LLM_PROVIDER: str = "gemini"  # Options: "mock", "deepseek", "gemini", "openai"
    
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

settings = Settings()

# Ensure storage directories exist
def ensure_storage_dirs():
    """Create storage directories if they don't exist"""
    from pathlib import Path
    
    # Create main storage directory
    Path(settings.STORAGE_DIR).mkdir(exist_ok=True)
    
    # Create memory subdirectory
    Path(settings.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    # Create vectordb subdirectory
    Path(settings.CHROMA_PATH).mkdir(parents=True, exist_ok=True)

# Auto-create directories on import
ensure_storage_dirs()
