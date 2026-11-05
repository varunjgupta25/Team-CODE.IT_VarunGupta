import os
from typing import List, Optional, Union
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "RepairBuddy API"
    ENV: Optional[str] = None
    ENVIRONMENT: Optional[str] = None
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS Configuration
    ALLOWED_ORIGINS: Optional[Union[str, List[str]]] = None
    CORS_ORIGINS: Optional[Union[str, List[str]]] = None
    CORS_ORIGIN_REGEX: Optional[str] = r"https://.*\.vercel\.app"

    # Database / Firebase Admin Configuration
    FIREBASE_CREDENTIALS_PATH: str = ""
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = None
    FIRESTORE_PROJECT_ID: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    USE_MOCK_FIREBASE: bool = True
    AUTO_SEED: bool = True

    # Transit Speed in km/h for ETA calculation (PRD: 25 km/h)
    TRANSIT_SPEED_KMH: float = 25.0

    # Trust Engine & Bayesian Rating Parameters
    BAYESIAN_GLOBAL_MEAN: float = 4.5
    BAYESIAN_MIN_WEIGHT: float = 5.0
    AUTO_FLAG_THRESHOLD: int = 3
    AUTO_FLAG_WINDOW_HOURS: int = 48

    def __init__(self, **values):
        explicit_env = values.get("ENV")
        explicit_environment = values.get("ENVIRONMENT")
        super().__init__(**values)

        # pydantic-settings may load CI environment variables over constructor
        # values; preserve explicit settings used by tests and programmatic callers.
        if explicit_env is not None or explicit_environment is not None:
            resolved_env = (explicit_env or explicit_environment or "development").strip().lower()
            self.ENV = resolved_env
            self.ENVIRONMENT = resolved_env
            if resolved_env in ["production", "staging"]:
                dev_defaults = {
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                }
                self.ALLOWED_ORIGINS = [
                    origin for origin in self.ALLOWED_ORIGINS or []
                    if origin not in dev_defaults
                ]
                self.CORS_ORIGINS = list(self.ALLOWED_ORIGINS)

    @model_validator(mode="after")
    def assemble_environment_and_cors(self) -> "Settings":
        # 1. Standardize ENV / ENVIRONMENT
        resolved_env = (self.ENV or self.ENVIRONMENT or "development").strip().lower()
        self.ENV = resolved_env
        self.ENVIRONMENT = resolved_env

        # 2. Synchronize credentials JSON alias
        if not self.FIREBASE_CREDENTIALS_JSON and self.GOOGLE_APPLICATION_CREDENTIALS_JSON:
            self.FIREBASE_CREDENTIALS_JSON = self.GOOGLE_APPLICATION_CREDENTIALS_JSON

        # 3. Gather origins: ALLOWED_ORIGINS takes precedence over CORS_ORIGINS
        selected_source = self.ALLOWED_ORIGINS if self.ALLOWED_ORIGINS is not None else self.CORS_ORIGINS
        raw_origins: List[str] = []
        if isinstance(selected_source, str):
            raw_origins.extend([item.strip() for item in selected_source.split(",") if item.strip()])
        elif isinstance(selected_source, list):
            raw_origins.extend([str(item).strip() for item in selected_source if str(item).strip()])

        # Remove wildcards completely - reject '*' and wildcard origins
        clean_origins: List[str] = []
        for origin in raw_origins:
            if origin != "*" and origin not in clean_origins:
                clean_origins.append(origin)

        # 4. Dynamic CORS resolution based on environment
        dev_defaults = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

        if self.ENV == "development":
            # Provide sensible development defaults ONLY when ENVIRONMENT=development
            if not clean_origins:
                clean_origins = list(dev_defaults)
            else:
                for default_origin in dev_defaults:
                    if default_origin not in clean_origins:
                        clean_origins.append(default_origin)
        elif self.ENV in ["production", "staging"]:
            # Strictly reject requests from non-whitelisted origins in production environments
            pass

        self.ALLOWED_ORIGINS = clean_origins
        self.CORS_ORIGINS = clean_origins
        return self


settings = Settings()
