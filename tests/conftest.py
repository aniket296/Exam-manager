import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import json

from backend.main import app
from backend.models import Base, get_db, PaperModel
from backend.config import settings
from backend.utils.time import utc_now
from tests.fixtures.mock_razorpay import (
    generate_mock_webhook_payload, generate_webhook_signature,
    generate_tampered_webhook_signature, generate_checkout_signature
)
from tests.fixtures.mock_sheets import MockSpreadsheet

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def sample_paper(db_session):
    """Creates a comprehensive sample paper with both MCQ and multi-alias Text questions."""
    questions = [
        {
            "QuestionID": "Q101",
            "QuestionText": "What is the square root of 64?",
            "Type": "MCQ",
            "Options": [
                {"OptionID": "OPT_A", "Text": "6"},
                {"OptionID": "OPT_B", "Text": "8"},
                {"OptionID": "OPT_C", "Text": "10"}
            ],
            "CorrectAnswer": "OPT_B",
            "MarksCorrect": 4.0,
            "MarksNegative": 1.0
        },
        {
            "QuestionID": "Q102",
            "QuestionText": "Which nation has Washington, D.C. as its capital?",
            "Type": "Text",
            "Options": [],
            "CorrectAnswer": "usa,us,united states,united states of america",
            "MarksCorrect": 4.0,
            "MarksNegative": 1.0
        },
        {
            "QuestionID": "Q103",
            "QuestionText": "Is water composed of Hydrogen and Oxygen?",
            "Type": "MCQ",
            "Options": [
                {"OptionID": "OPT_Y", "Text": "Yes"},
                {"OptionID": "OPT_N", "Text": "No"}
            ],
            "CorrectAnswer": "OPT_Y",
            "MarksCorrect": 2.0,
            "MarksNegative": 0.5
        }
    ]

    p = PaperModel(
        PaperID="pap_suite_01",
        Title="Core Assessment Suite Paper",
        PriceMinorUnits=5000,
        Currency="INR",
        TimeLimitMinutes=20,
        Status="PUBLISHED",
        Version=1,
        NegativeMarkingEnabled=True,
        ShowAnswerKey=True,
        AllowResume=True,
        AntiCheatPolicy="AUTO_SUBMIT_ON_3",
        QuestionsJSON=json.dumps(questions),
        CreatedAt=utc_now(),
        UpdatedAt=utc_now()
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p

