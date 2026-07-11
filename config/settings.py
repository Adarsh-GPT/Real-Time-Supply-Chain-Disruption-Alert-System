# config/settings.py
"""Central application settings loaded from .env"""
from __future__ import annotations
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Firebase
    firebase_api_key: str = Field(default="")
    firebase_project_id: str = Field(default="")
    firebase_credentials_path: Path = Field(default=PROJECT_ROOT / "firebase-credentials.json")
    firebase_credentials_json: str = Field(default="")

    # News APIs
    newsapi_key: str = Field(default="")
    guardian_key: str = Field(default="")
    gnews_key: str = Field(default="")

    # App
    fetch_interval_minutes: int = Field(default=15)
    max_articles_per_source: int = Field(default=20)
    env: str = Field(default="development")

    # Alerts
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def has_firebase(self) -> bool:
        if not self.firebase_project_id or not self.firebase_api_key:
            return False
        if "your_" in self.firebase_project_id.lower() or "your_" in self.firebase_api_key.lower():
            return False
        return True

    @property
    def has_newsapi(self) -> bool:
        return bool(self.newsapi_key)

    @property
    def model_path(self) -> Path:
        return PROJECT_ROOT / "model"

settings = Settings()
