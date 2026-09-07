from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from backend.models import get_db, AttemptModel
from backend.schemas import (
    ExamStartResponse, HeartbeatRequest, HeartbeatResponse,
    AntiCheatEventRequest, AntiCheatEventResponse,
    ExamSubmitRequest, ExamResultResponse
)
from backend.security.attempt_auth import get_current_attempt
from backend.security.rate_limit import check_rate_limit
from backend.services.exam_service import exam_service

router = APIRouter(prefix="/exam", tags=["Exam"])

@router.get("", response_model=ExamStartResponse)
def get_or_start_exam(
    request: Request,
    attempt: AttemptModel = Depends(get_current_attempt),
    db: Session = Depends(get_db)
):
    """
    Starts or resumes an assessment attempt.
    Freezes randomized question & option ordering on first start.
    Returns exam-safe sanitized questions with server-authoritative timer.
    """
    check_rate_limit(request, max_requests=30, window_seconds=60)
    data = exam_service.get_or_start_exam(attempt, db)
    return ExamStartResponse(**data)

@router.post("/heartbeat", response_model=HeartbeatResponse)
def exam_heartbeat(
    payload: HeartbeatRequest,
    request: Request,
    attempt: AttemptModel = Depends(get_current_attempt),
    db: Session = Depends(get_db)
):
    """
    Periodic heartbeat to update last-seen timestamp and synchronize official timer.
    """
    check_rate_limit(request, max_requests=60, window_seconds=60)
    data = exam_service.record_heartbeat(attempt, payload.SessionID, db)
    return HeartbeatResponse(**data)

@router.post("/event", response_model=AntiCheatEventResponse)
def log_anti_cheat_event(
    payload: AntiCheatEventRequest,
    request: Request,
    attempt: AttemptModel = Depends(get_current_attempt),
    db: Session = Depends(get_db)
):
    """
    Logs deterrence anti-cheat events (fullscreen exit, tab hidden, blur).
    Enforces strike policy with friendly student messages.
    """
    check_rate_limit(request, max_requests=40, window_seconds=60)
    data = exam_service.record_anti_cheat_event(
        attempt=attempt,
        event_type=payload.EventType,
        details=payload.Details or "",
        db=db
    )
    return AntiCheatEventResponse(**data)

@router.post("/submit", response_model=ExamResultResponse)
def submit_exam(
    payload: ExamSubmitRequest,
    request: Request,
    attempt: AttemptModel = Depends(get_current_attempt),
    db: Session = Depends(get_db)
):
    """
    Authoritative test submission and grading.
    Idempotent: repeated clicks return previously evaluated result safely.
    """
    check_rate_limit(request, max_requests=10, window_seconds=60)
    data = exam_service.submit_exam(attempt, payload.Answers, db)
    return ExamResultResponse(**data)

# --- Direct Paper & Submit Endpoints (Suites 1 & 2) ---

@router.get("/paper/{paper_id}/{payment_id}")
def get_paper_by_payment(
    paper_id: str,
    payment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Direct student exam access by payment reference.
    Enforces status transitions, session checks, and guarantees zero leakage of answer/marks metadata.
    """
    from backend.models import OrderModel
    x_session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")

    attempt = db.query(AttemptModel).filter(
        AttemptModel.PaperID == paper_id,
        (AttemptModel.PaymentID == payment_id) | (AttemptModel.OrderID == payment_id)
    ).first()

    if not attempt:
        order = db.query(OrderModel).filter(
            OrderModel.PaperID == paper_id,
            (OrderModel.PaymentID == payment_id) | (OrderModel.OrderID == payment_id)
        ).first()
        if order and order.Status == "CREATED":
            raise HTTPException(status_code=401, detail="Payment has not been completed.")
        raise HTTPException(status_code=404, detail="Exam pass not found.")

    exam_data = exam_service.get_or_start_exam(attempt, db, requested_session_id=x_session_id)

    # Strictly sanitize questions: omit CorrectAnswer, MarksCorrect, MarksNegative (Suite 1)
    sanitized_questions = []
    for q in exam_data["Questions"]:
        sanitized_questions.append({
            "QuestionID": q.QuestionID,
            "QuestionText": q.QuestionText,
            "ImageURL": q.ImageURL,
            "ImageAltText": q.ImageAltText,
            "Type": q.Type,
            "Options": [{"OptionID": opt.OptionID, "Text": opt.Text} for opt in q.Options]
        })

    return {
        "AttemptID": exam_data["AttemptID"],
        "PaperID": exam_data["PaperID"],
        "PaperTitle": exam_data["PaperTitle"],
        "StudentName": exam_data["StudentName"],
        "TimeLimitMinutes": exam_data["TimeLimitMinutes"],
        "StartedAt": exam_data["StartedAt"],
        "Deadline": exam_data["Deadline"],
        "SessionID": exam_data["SessionID"],
        "Questions": sanitized_questions
    }

@router.post("/submit/{paper_id}/{payment_id}", response_model=ExamResultResponse)
def submit_paper_by_payment(
    paper_id: str,
    payment_id: str,
    payload: ExamSubmitRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Direct student exam submission by payment reference.
    """
    attempt = db.query(AttemptModel).filter(
        AttemptModel.PaperID == paper_id,
        (AttemptModel.PaymentID == payment_id) | (AttemptModel.OrderID == payment_id)
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Exam pass not found.")

    data = exam_service.submit_exam(attempt, payload.Answers, db)
    return ExamResultResponse(**data)

