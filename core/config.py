import os
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "RepairBuddy API"
    ENV: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173"
    CORS_ORIGIN_REGEX: Optional[str] = r"https://.*\.vercel\.app"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Auto-seed configuration on startup
    AUTO_SEED: bool = True

    # Firebase Admin Configuration
    FIREBASE_CREDENTIALS_PATH: str = ""
    USE_MOCK_FIREBASE: bool = True

    # Transit Speed in km/h for ETA calculation (PRD: 25 km/h)
    TRANSIT_SPEED_KMH: float = 25.0


settings = Settings()
