import os
from pydantic_settings import BaseSettings

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
