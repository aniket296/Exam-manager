import os

os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_sample_key_id")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "rzp_test_sample_key_secret")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "whsec_sample_secret_key")
os.environ.setdefault("RAZORPAY_SIMULATION_MODE", "true")
os.environ.setdefault(
    "ADMIN_PASSWORD_HASH",
    "pbkdf2_sha256$600000$c4c820ee808561dbd8d0a45c581410a7$bf0818d41223b6f739ec0370711f5b8a71ad8047a60c94cc8f5a21800c86b41f"
)
os.environ.setdefault("ADMIN_SECRET_KEY", "temporary_admin_secret_key_change_in_prod_at_least_32_chars")
os.environ.setdefault("ATTEMPT_SECRET_KEY", "temporary_attempt_secret_key_change_in_prod_at_least_32_chars")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models import Base, get_db

# Test in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh, empty in-memory database for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

