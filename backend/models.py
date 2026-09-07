from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from backend.config import settings

Base = declarative_base()

class PaperModel(Base):
    __tablename__ = "papers"

    PaperID = Column(String(64), primary_key=True, index=True)
    Title = Column(String(255), nullable=False)
    PriceMinorUnits = Column(Integer, nullable=False, default=0)
    Currency = Column(String(8), nullable=False, default="INR")
    TimeLimitMinutes = Column(Integer, nullable=False, default=30)
    Status = Column(String(16), nullable=False, default="DRAFT", index=True)  # DRAFT, PUBLISHED, ARCHIVED
    Version = Column(Integer, nullable=False, default=1)
    NegativeMarkingEnabled = Column(Boolean, nullable=False, default=False)
    ShowAnswerKey = Column(Boolean, nullable=False, default=False)
    AllowResume = Column(Boolean, nullable=False, default=True)
    AntiCheatPolicy = Column(String(32), nullable=False, default="AUTO_SUBMIT_ON_3")
    QuestionsJSON = Column(Text, nullable=False, default="[]")
    CreatedAt = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    UpdatedAt = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class OrderModel(Base):
    __tablename__ = "orders"

    OrderID = Column(String(64), primary_key=True, index=True)
    PaperID = Column(String(64), ForeignKey("papers.PaperID"), nullable=False)
    PaperVersion = Column(Integer, nullable=False, default=1)
    AmountMinorUnits = Column(Integer, nullable=False)
    Currency = Column(String(8), nullable=False, default="INR")
    Status = Column(String(16), nullable=False, default="CREATED", index=True)  # CREATED, PAID, FAILED, EXPIRED, REFUNDED
    StudentName = Column(String(128), nullable=False)
    StudentIdentifier = Column(String(64), nullable=True)
    Contact = Column(String(64), nullable=True)
    PaymentID = Column(String(64), nullable=True, index=True)
    CreatedAt = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ExpiresAt = Column(DateTime(timezone=True), nullable=False)

class AttemptModel(Base):
    __tablename__ = "attempts"

    AttemptID = Column(String(64), primary_key=True, index=True)
    OrderID = Column(String(64), unique=True, index=True, nullable=False)
    PaymentID = Column(String(64), unique=True, index=True, nullable=False)
    Name = Column(String(128), nullable=False)
    StudentIdentifier = Column(String(64), nullable=True)
    PhoneOrContact = Column(String(64), nullable=True)
    PaperID = Column(String(64), ForeignKey("papers.PaperID"), nullable=False)
    PaperVersion = Column(Integer, nullable=False)
    AmountMinorUnits = Column(Integer, nullable=False)
    Currency = Column(String(8), nullable=False, default="INR")
    Status = Column(String(16), nullable=False, default="PAID", index=True)  # PAID, STARTED, COMPLETED, EXPIRED
    AttemptTokenHash = Column(String(128), unique=True, index=True, nullable=False)
    TokenCreatedAt = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    TokenExpiresAt = Column(DateTime(timezone=True), nullable=False)
    StartedAt = Column(DateTime(timezone=True), nullable=True)
    Deadline = Column(DateTime(timezone=True), nullable=True)
    CompletedAt = Column(DateTime(timezone=True), nullable=True)
    Score = Column(Float, nullable=True)
    MaxMarks = Column(Float, nullable=True)
    CorrectCount = Column(Integer, nullable=True)
    WrongCount = Column(Integer, nullable=True)
    UnansweredCount = Column(Integer, nullable=True)
    StrikeCount = Column(Integer, nullable=False, default=0)
    SessionID = Column(String(64), nullable=True)
    LastSeenAt = Column(DateTime(timezone=True), nullable=True)
    QuestionOrderJSON = Column(Text, nullable=True)
    OptionOrderJSON = Column(Text, nullable=True)
    AnswersJSON = Column(Text, nullable=True)
    SubmissionHash = Column(String(128), nullable=True)
    Timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class WebhookEventModel(Base):
    __tablename__ = "webhook_events"

    EventID = Column(String(64), primary_key=True, index=True)
    EventType = Column(String(64), nullable=False)
    OrderID = Column(String(64), nullable=True)
    PaymentID = Column(String(64), nullable=True)
    ReceivedAt = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ProcessedAt = Column(DateTime(timezone=True), nullable=True)
    ProcessingStatus = Column(String(32), nullable=False, default="PROCESSED")  # PROCESSED, IGNORED, FAILED
    ErrorMessage = Column(Text, nullable=True)

class AdminSessionModel(Base):
    __tablename__ = "admin_sessions"

    SessionToken = Column(String(128), primary_key=True, index=True)
    CreatedAt = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ExpiresAt = Column(DateTime(timezone=True), nullable=False)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

