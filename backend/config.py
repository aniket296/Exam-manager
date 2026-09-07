from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server & Environment
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"

    # Razorpay Keys
    # Safe defaults are intentionally blank so production never runs with known demo credentials.
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_SIMULATION_MODE: bool = False

    # Google Sheets
    GOOGLE_SHEET_ID: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_PATH: Optional[str] = None

    # Admin Security
    # Empty by default so we fail closed unless secrets are explicitly configured.
    ADMIN_PASSWORD_HASH: str = ""
    ADMIN_SESSION_EXPIRE_MINUTES: int = 120
    ADMIN_SECRET_KEY: str = ""

    # Attempt Security
    ATTEMPT_TOKEN_EXPIRE_HOURS: int = 24
    ATTEMPT_SECRET_KEY: str = ""

    # Transactional DB
    DATABASE_URL: str = "sqlite:///./exam_manager.db"

    # Validation Limits
    MAX_QUESTIONS_PER_PAPER: int = 100
    MAX_OPTIONS_PER_QUESTION: int = 8
    MAX_QUESTION_TEXT_LENGTH: int = 4000
    MAX_OPTION_TEXT_LENGTH: int = 1000
    MAX_TEXT_ANSWER_LENGTH: int = 500
    MAX_REQUEST_BODY_SIZE: int = 2 * 1024 * 1024  # 2MB

settings = Settings()
