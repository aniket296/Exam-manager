from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Literal
from datetime import datetime
import re

# Question Schemas
class OptionItem(BaseModel):
    OptionID: str = Field(..., min_length=1, max_length=64)
    Text: str = Field(..., min_length=1, max_length=1000)

class Question(BaseModel):
    QuestionID: str = Field(..., min_length=1, max_length=64)
    QuestionText: str = Field(..., min_length=1, max_length=4000)
    ImageURL: Optional[str] = Field("", max_length=1000)
    ImageAltText: Optional[str] = Field("", max_length=500)
    Type: Literal["MCQ", "Text"]
    Options: List[OptionItem] = Field(default_factory=list)
    CorrectAnswer: str = Field(..., min_length=1, max_length=1000)
    MarksCorrect: float = Field(default=4.0, ge=0)
    MarksNegative: float = Field(default=1.0, ge=0)

    @field_validator("ImageURL")
    @classmethod
    def validate_image_url(cls, v: Optional[str]) -> Optional[str]:
        if not v or v.strip() == "":
            return ""
        v = v.strip()
        if not (v.startswith("https://") or v.startswith("/") or v.startswith("http://localhost")):
            raise ValueError("ImageURL must use HTTPS or safe relative path")
        return v

    @model_validator(mode="after")
    def validate_type_and_options(self) -> "Question":
        if self.Type == "MCQ":
            if not self.Options or len(self.Options) < 2:
                raise ValueError("MCQ questions must have at least 2 options")
            if len(self.Options) > 8:
                raise ValueError("MCQ questions cannot have more than 8 options")
            option_ids = [opt.OptionID for opt in self.Options]
            if len(option_ids) != len(set(option_ids)):
                raise ValueError("OptionIDs within a question must be unique")
            if self.CorrectAnswer not in option_ids:
                raise ValueError(f"CorrectAnswer '{self.CorrectAnswer}' must match one of the OptionIDs")
        elif self.Type == "Text":
            if self.Options and len(self.Options) > 0:
                raise ValueError("Text questions must not have MCQ options")
            if not self.CorrectAnswer.strip():
                raise ValueError("Text question must specify at least one valid correct answer")
        return self

# Exam-safe Question (No CorrectAnswer or hidden marks metadata)
class ExamSafeOption(BaseModel):
    OptionID: str
    Text: str

class ExamSafeQuestion(BaseModel):
    QuestionID: str
    QuestionText: str
    ImageURL: Optional[str] = ""
    ImageAltText: Optional[str] = ""
    Type: Literal["MCQ", "Text"]
    Options: List[ExamSafeOption] = Field(default_factory=list)
    MarksCorrect: float
    MarksNegative: float

# Paper Schemas
class PaperCreateRequest(BaseModel):
    Title: str = Field(..., min_length=3, max_length=255)
    PriceMinorUnits: int = Field(default=0, ge=0)
    Currency: str = Field(default="INR", max_length=8)
    TimeLimitMinutes: int = Field(default=30, ge=1, le=300)
    NegativeMarkingEnabled: bool = Field(default=False)
    ShowAnswerKey: bool = Field(default=False)
    AllowResume: bool = Field(default=True)
    AntiCheatPolicy: Literal["WARNING_ONLY", "AUTO_SUBMIT_ON_3", "AUTO_SUBMIT_ON_5"] = "AUTO_SUBMIT_ON_3"
    Questions: List[Question] = Field(default_factory=list)

    @field_validator("Questions")
    @classmethod
    def validate_questions_list(cls, v: List[Question]) -> List[Question]:
        if len(v) > 100:
            raise ValueError("A paper cannot contain more than 100 questions")
        qids = [q.QuestionID for q in v]
        if len(qids) != len(set(qids)):
            raise ValueError("All QuestionIDs within a paper must be unique")
        return v

class PaperUpdateRequest(BaseModel):
    Title: Optional[str] = Field(None, min_length=3, max_length=255)
    PriceMinorUnits: Optional[int] = Field(None, ge=0)
    Currency: Optional[str] = Field(None, max_length=8)
    TimeLimitMinutes: Optional[int] = Field(None, ge=1, le=300)
    NegativeMarkingEnabled: Optional[bool] = None
    ShowAnswerKey: Optional[bool] = None
    AllowResume: Optional[bool] = None
    AntiCheatPolicy: Optional[Literal["WARNING_ONLY", "AUTO_SUBMIT_ON_3", "AUTO_SUBMIT_ON_5"]] = None
    Questions: Optional[List[Question]] = None

    @field_validator("Questions")
    @classmethod
    def validate_questions_list(cls, v: Optional[List[Question]]) -> Optional[List[Question]]:
        if v is None:
            return v
        if len(v) > 100:
            raise ValueError("A paper cannot contain more than 100 questions")
        qids = [q.QuestionID for q in v]
        if len(qids) != len(set(qids)):
            raise ValueError("All QuestionIDs within a paper must be unique")
        return v

class PaperPublicSummary(BaseModel):
    PaperID: str
    Title: str
    PriceMinorUnits: int
    Currency: str
    TimeLimitMinutes: int
    QuestionCount: int
    NegativeMarkingEnabled: bool
    ShowAnswerKey: bool
    AntiCheatPolicy: str

class PaperDetailAdmin(BaseModel):
    PaperID: str
    Title: str
    PriceMinorUnits: int
    Currency: str
    TimeLimitMinutes: int
    Status: str
    Version: int
    NegativeMarkingEnabled: bool
    ShowAnswerKey: bool
    AllowResume: bool
    AntiCheatPolicy: str
    Questions: List[Question]
    CreatedAt: Optional[str] = None
    UpdatedAt: Optional[str] = None

# Payments Schemas
class PaymentCreateOrderRequest(BaseModel):
    PaperID: str = Field(..., min_length=1, max_length=64)
    StudentName: str = Field(..., min_length=2, max_length=128)
    StudentIdentifier: Optional[str] = Field("", max_length=64)
    Contact: Optional[str] = Field("", max_length=64)

class PaymentCreateOrderResponse(BaseModel):
    OrderID: str
    PaperID: str
    Title: str
    AmountMinorUnits: int
    Currency: str
    KeyID: str
    SimulationMode: bool = False
    SimulationToken: Optional[str] = None

class PaymentVerifyRequest(BaseModel):
    OrderID: str = Field(..., min_length=1, max_length=64)
    PaymentID: str = Field(..., min_length=1, max_length=64)
    Signature: str = Field(..., min_length=1, max_length=256)
    SimulationToken: Optional[str] = Field(None, max_length=256)

class PaymentVerifyResponse(BaseModel):
    Success: bool
    AttemptToken: str
    AttemptID: str
    Message: str

# Exam Schemas
class ExamStartResponse(BaseModel):
    AttemptID: str
    PaperID: str
    PaperTitle: str
    StudentName: str
    TimeLimitMinutes: int
    StartedAt: str
    Deadline: str
    NegativeMarkingEnabled: bool
    AntiCheatPolicy: str
    Questions: List[ExamSafeQuestion]
    SessionID: str

class HeartbeatRequest(BaseModel):
    SessionID: Optional[str] = None
    CurrentQuestionID: Optional[str] = None

class HeartbeatResponse(BaseModel):
    Status: str
    RemainingSeconds: int
    StrikeCount: int
    Deadline: str

class AntiCheatEventRequest(BaseModel):
    EventType: Literal["FULLSCREEN_EXIT", "TAB_HIDDEN", "WINDOW_BLUR", "COPY_ATTEMPT", "PASTE_ATTEMPT"]
    Details: Optional[str] = Field("", max_length=256)

class AntiCheatEventResponse(BaseModel):
    Recorded: bool
    StrikeCount: int
    ActionTaken: str  # e.g., "WARNING", "AUTO_SUBMITTED"
    FriendlyMessage: str

class ExamSubmitRequest(BaseModel):
    Answers: Dict[str, str] = Field(default_factory=dict)

class QuestionResultItem(BaseModel):
    QuestionID: str
    QuestionText: str
    Type: str
    StudentAnswer: Optional[str] = None
    IsCorrect: bool
    MarksAwarded: float
    CorrectAnswer: Optional[str] = None  # Populated ONLY if ShowAnswerKey is True

class ExamResultResponse(BaseModel):
    AttemptID: str
    StudentName: str
    PaperTitle: str
    Score: float
    MaxMarks: float
    Percentage: float
    CorrectCount: int
    WrongCount: int
    UnansweredCount: int
    CompletedAt: str
    ShowAnswerKey: bool
    QuestionBreakdown: Optional[List[QuestionResultItem]] = None

# Admin Auth Schemas
class AdminLoginRequest(BaseModel):
    Password: str = Field(..., min_length=1, max_length=128)

class AdminLoginResponse(BaseModel):
    Token: str
    ExpiresAt: str

