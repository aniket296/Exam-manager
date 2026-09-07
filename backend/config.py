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
    RAZORPAY_KEY_ID: str = "rzp_test_sample_key_id"
    RAZORPAY_KEY_SECRET: str = "rzp_test_sample_key_secret"
    RAZORPAY_WEBHOOK_SECRET: str = "whsec_sample_secret_key"
    RAZORPAY_SIMULATION_MODE: bool = True  # Allows offline/demo testing without live Razorpay account

    # Google Sheets
    GOOGLE_SHEET_ID: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_PATH: Optional[str] = None

    # Admin Security
    # Default hashed password for "Admin@12345"
    ADMIN_PASSWORD_HASH: str = "pbkdf2_sha256$600000$c4c820ee808561dbd8d0a45c581410a7$bf0818d41223b6f739ec0370711f5b8a71ad8047a60c94cc8f5a21800c86b41f"
    ADMIN_SESSION_EXPIRE_MINUTES: int = 120
    ADMIN_SECRET_KEY: str = "antigravity_admin_secret_key_at_least_32_bytes_long_change_me"

    # Attempt Security
    ATTEMPT_TOKEN_EXPIRE_HOURS: int = 24
    ATTEMPT_SECRET_KEY: str = "antigravity_attempt_secret_key_at_least_32_bytes_long_change_me"

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
