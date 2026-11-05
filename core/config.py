from typing import Any, List, Optional, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "RepairBuddy API"
    ENV: str = "development"
    ENVIRONMENT: Optional[str] = None
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = ""
    CORS_ORIGIN_REGEX: Optional[str] = r"https://.*\.vercel\.app"

    @model_validator(mode="before")
    @classmethod
    def resolve_environment_fields(cls, values: Any):
        if not isinstance(values, dict):
            return values
        explicit_env = values.get("ENV")
        if not explicit_env:
            environment = values.get("ENVIRONMENT")
            if environment:
                values["ENV"] = environment
        if not values.get("ENVIRONMENT") and values.get("ENV"):
            values["ENVIRONMENT"] = values["ENV"]
        return values

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]], info) -> List[str]:
        if isinstance(v, str):
            origins = [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = [i.strip() for i in v if isinstance(i, str) and i.strip()]
        else:
            origins = []

        origins = [origin for origin in origins if origin != "*"]

        env_value = str((info.data or {}).get("ENV", "development")).lower()
        if env_value == "development":
            for dev_origin in [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
            ]:
                if dev_origin not in origins:
                    origins.append(dev_origin)
        return origins

    # Auto-seed configuration on startup
    AUTO_SEED: bool = True

    # Firebase Admin Configuration
    FIREBASE_CREDENTIALS_JSON: str = ""
    FIREBASE_CREDENTIALS_PATH: str = ""
    USE_MOCK_FIREBASE: bool = True

    # Transit Speed in km/h for ETA calculation (PRD: 25 km/h)
    TRANSIT_SPEED_KMH: float = 25.0

    # Auto-confirm period in hours for awaiting_confirmation jobs
    AUTO_CONFIRM_HOURS: float = 48.0

    # Private Storage Configuration (DPDP compliant)
    PRIVATE_STORAGE_PATH: str = "data/private_uploads"
    FIREBASE_STORAGE_BUCKET: str = ""

    # SOS Alerting & Notification Provider Configuration
    OPS_ALERT_PHONE: str = "+919800000000"
    NOTIFICATION_PROVIDER: str = "console"  # "console" | "twilio"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_PHONE: str = ""
    TWILIO_WHATSAPP_FROM: str = ""


settings = Settings()
