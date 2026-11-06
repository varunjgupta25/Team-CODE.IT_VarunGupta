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
    CUSTOMER_APP_ORIGIN: Optional[Union[str, List[str]]] = None
    PARTNER_APP_ORIGIN: Optional[Union[str, List[str]]] = None
    CORS_ORIGIN_REGEX: Optional[str] = None

    # Database / Firebase Admin Configuration
    FIREBASE_CREDENTIALS_PATH: str = ""
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = None
    FIRESTORE_PROJECT_ID: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    USE_MOCK_FIREBASE: bool = True
    AUTO_SEED: bool = False

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
        explicit_origins = values.get("ALLOWED_ORIGINS")
        if explicit_origins is None:
            explicit_origins = values.get("CORS_ORIGINS")
        explicit_cust = values.get("CUSTOMER_APP_ORIGIN")
        explicit_partner = values.get("PARTNER_APP_ORIGIN")
        super().__init__(**values)

        # Pydantic-settings may load CI environment variables over constructor
        # values; preserve explicit settings used by tests and programmatic callers.
        if explicit_env is not None or explicit_environment is not None:
            resolved_env = (explicit_env or explicit_environment or "development").strip().lower()
            self.ENV = resolved_env
            self.ENVIRONMENT = resolved_env
            if resolved_env in ["production", "staging"]:
                raw_list: List[str] = []
                for src in [
                    explicit_origins if explicit_origins is not None else self.ALLOWED_ORIGINS,
                    explicit_cust if explicit_cust is not None else self.CUSTOMER_APP_ORIGIN,
                    explicit_partner if explicit_partner is not None else self.PARTNER_APP_ORIGIN,
                ]:
                    if isinstance(src, str):
                        raw_list.extend([item.strip() for item in src.split(",") if item.strip()])
                    elif isinstance(src, list):
                        raw_list.extend([str(item).strip() for item in src if str(item).strip()])
                clean_origins = []
                for origin in raw_list:
                    if origin != "*" and origin not in clean_origins:
                        if resolved_env in ["production", "staging"] and ("localhost" in origin or "127.0.0.1" in origin):
                            continue
                        clean_origins.append(origin)
                self.ALLOWED_ORIGINS = clean_origins
                self.CORS_ORIGINS = list(clean_origins)
                if "CORS_ORIGIN_REGEX" not in values and self.CORS_ORIGIN_REGEX == r"https://.*\.vercel\.app":
                    self.CORS_ORIGIN_REGEX = None

    @model_validator(mode="after")
    def assemble_environment_and_cors(self) -> "Settings":
        # 1. Standardize ENV / ENVIRONMENT
        resolved_env = (self.ENV or self.ENVIRONMENT or "development").strip().lower()
        self.ENV = resolved_env
        self.ENVIRONMENT = resolved_env

        # 2. Synchronize credentials JSON alias
        if not self.FIREBASE_CREDENTIALS_JSON and self.GOOGLE_APPLICATION_CREDENTIALS_JSON:
            self.FIREBASE_CREDENTIALS_JSON = self.GOOGLE_APPLICATION_CREDENTIALS_JSON

        # 3. Gather origins: ALLOWED_ORIGINS, CORS_ORIGINS, CUSTOMER_APP_ORIGIN, PARTNER_APP_ORIGIN
        selected_source = self.ALLOWED_ORIGINS if self.ALLOWED_ORIGINS is not None else self.CORS_ORIGINS
        raw_origins: List[str] = []
        for src in [selected_source, self.CUSTOMER_APP_ORIGIN, self.PARTNER_APP_ORIGIN]:
            if isinstance(src, str):
                raw_origins.extend([item.strip() for item in src.split(",") if item.strip()])
            elif isinstance(src, list):
                raw_origins.extend([str(item).strip() for item in src if str(item).strip()])

        # Remove wildcards completely - reject '*' and wildcard origins
        clean_origins: List[str] = []
        for origin in raw_origins:
            if origin != "*" and origin not in clean_origins:
                if self.ENV in ["production", "staging"] and ("localhost" in origin or "127.0.0.1" in origin):
                    continue
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
            # Disable automatic seeding in production
            self.AUTO_SEED = False
            # Disable permissive default regex in production unless explicitly configured
            if self.CORS_ORIGIN_REGEX == r"https://.*\.vercel\.app":
                self.CORS_ORIGIN_REGEX = None

        self.ALLOWED_ORIGINS = clean_origins
        self.CORS_ORIGINS = clean_origins
        return self


settings = Settings()
