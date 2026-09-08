import json
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.models import get_db, PaperModel, AttemptModel, AdminSessionModel
from backend.schemas import (
    AdminLoginRequest, AdminLoginResponse,
    PaperCreateRequest, PaperUpdateRequest, PaperDetailAdmin, Question
)
from backend.security.admin_auth import (
    authenticate_admin_password, create_admin_session, get_current_admin
)
from backend.security.rate_limit import check_rate_limit
from backend.services.sheets_service import sheets_service
from backend.utils.time import utc_now, to_iso

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

@router.post("/login", response_model=AdminLoginResponse)
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Admin login with rate limiting (max 5 requests per minute)."""
    check_rate_limit(request, max_requests=5, window_seconds=60)
    if not authenticate_admin_password(payload.Password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin password."
        )
    token, expires_at = create_admin_session(db)
    return AdminLoginResponse(Token=token, ExpiresAt=expires_at)

@router.get("/papers", response_model=List[PaperDetailAdmin])
def list_admin_papers(
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lists all papers across all states (DRAFT, PUBLISHED, ARCHIVED)."""
    papers = db.query(PaperModel).order_by(PaperModel.CreatedAt.desc()).all()
    results = []
    for p in papers:
        raw_q = json.loads(p.QuestionsJSON or "[]")
        questions = [Question(**q) for q in raw_q]
        results.append(
            PaperDetailAdmin(
                PaperID=p.PaperID,
                Title=p.Title,
                PriceMinorUnits=p.PriceMinorUnits,
                Currency=p.Currency,
                TimeLimitMinutes=p.TimeLimitMinutes,
                Status=p.Status,
                Version=p.Version,
                NegativeMarkingEnabled=p.NegativeMarkingEnabled,
                ShowAnswerKey=p.ShowAnswerKey,
                AllowResume=p.AllowResume,
                AntiCheatPolicy=p.AntiCheatPolicy,
                Questions=questions,
                CreatedAt=to_iso(p.CreatedAt),
                UpdatedAt=to_iso(p.UpdatedAt)
            )
        )
    return results

@router.post("/create-paper", response_model=PaperDetailAdmin)
def create_paper(
    payload: PaperCreateRequest,
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Creates a new assessment paper in DRAFT state."""
    paper_id = f"pap_{uuid.uuid4().hex[:10]}"
    now = utc_now()
    questions_data = [q.model_dump() for q in payload.Questions]

    new_paper = PaperModel(
        PaperID=paper_id,
        Title=payload.Title,
        PriceMinorUnits=payload.PriceMinorUnits,
        Currency=payload.Currency,
        TimeLimitMinutes=payload.TimeLimitMinutes,
        Status="DRAFT",
        Version=1,
        NegativeMarkingEnabled=payload.NegativeMarkingEnabled,
        ShowAnswerKey=payload.ShowAnswerKey,
        AllowResume=payload.AllowResume,
        AntiCheatPolicy=payload.AntiCheatPolicy,
        QuestionsJSON=json.dumps(questions_data),
        CreatedAt=now,
        UpdatedAt=now
    )
    db.add(new_paper)
    db.commit()
    db.refresh(new_paper)

    # Sync to Google Sheets
    try:
        sheets_service.sync_paper({
            "PaperID": new_paper.PaperID,
            "Title": new_paper.Title,
            "PriceMinorUnits": new_paper.PriceMinorUnits,
            "Currency": new_paper.Currency,
            "TimeLimitMinutes": new_paper.TimeLimitMinutes,
            "Status": new_paper.Status,
            "Version": new_paper.Version,
            "NegativeMarkingEnabled": new_paper.NegativeMarkingEnabled,
            "ShowAnswerKey": new_paper.ShowAnswerKey,
            "AllowResume": new_paper.AllowResume,
            "AntiCheatPolicy": new_paper.AntiCheatPolicy,
            "QuestionsJSON": new_paper.QuestionsJSON,
            "CreatedAt": to_iso(new_paper.CreatedAt),
            "UpdatedAt": to_iso(new_paper.UpdatedAt)
        })
    except Exception:
        pass

    return PaperDetailAdmin(
        PaperID=new_paper.PaperID,
        Title=new_paper.Title,
        PriceMinorUnits=new_paper.PriceMinorUnits,
        Currency=new_paper.Currency,
        TimeLimitMinutes=new_paper.TimeLimitMinutes,
        Status=new_paper.Status,
        Version=new_paper.Version,
        NegativeMarkingEnabled=new_paper.NegativeMarkingEnabled,
        ShowAnswerKey=new_paper.ShowAnswerKey,
        AllowResume=new_paper.AllowResume,
        AntiCheatPolicy=new_paper.AntiCheatPolicy,
        Questions=payload.Questions,
        CreatedAt=to_iso(new_paper.CreatedAt),
        UpdatedAt=to_iso(new_paper.UpdatedAt)
    )

@router.get("/paper/{paper_id}", response_model=PaperDetailAdmin)
def get_admin_paper(
    paper_id: str,
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Retrieves full paper definition with questions for admin viewing/editing."""
    p = db.query(PaperModel).filter(PaperModel.PaperID == paper_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paper not found.")
    raw_q = json.loads(p.QuestionsJSON or "[]")
    questions = [Question(**q) for q in raw_q]
    return PaperDetailAdmin(
        PaperID=p.PaperID,
        Title=p.Title,
        PriceMinorUnits=p.PriceMinorUnits,
        Currency=p.Currency,
        TimeLimitMinutes=p.TimeLimitMinutes,
        Status=p.Status,
        Version=p.Version,
        NegativeMarkingEnabled=p.NegativeMarkingEnabled,
        ShowAnswerKey=p.ShowAnswerKey,
        AllowResume=p.AllowResume,
        AntiCheatPolicy=p.AntiCheatPolicy,
        Questions=questions,
        CreatedAt=to_iso(p.CreatedAt),
        UpdatedAt=to_iso(p.UpdatedAt)
    )

@router.put("/paper/{paper_id}", response_model=PaperDetailAdmin)
def update_draft_paper(
    paper_id: str,
    payload: PaperUpdateRequest,
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Updates a paper. Only DRAFT papers can be edited in place."""
    p = db.query(PaperModel).filter(PaperModel.PaperID == paper_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paper not found.")
    if p.Status != "DRAFT":
        raise HTTPException(
            status_code=400,
            detail="Published or Archived papers cannot be edited in place. Please duplicate to create a new draft."
        )

    if payload.Title is not None:
        p.Title = payload.Title
    if payload.PriceMinorUnits is not None:
        p.PriceMinorUnits = payload.PriceMinorUnits
    if payload.Currency is not None:
        p.Currency = payload.Currency
    if payload.TimeLimitMinutes is not None:
        p.TimeLimitMinutes = payload.TimeLimitMinutes
    if payload.NegativeMarkingEnabled is not None:
        p.NegativeMarkingEnabled = payload.NegativeMarkingEnabled
    if payload.ShowAnswerKey is not None:
        p.ShowAnswerKey = payload.ShowAnswerKey
    if payload.AllowResume is not None:
        p.AllowResume = payload.AllowResume
    if payload.AntiCheatPolicy is not None:
        p.AntiCheatPolicy = payload.AntiCheatPolicy
    if payload.Questions is not None:
        p.QuestionsJSON = json.dumps([q.model_dump() for q in payload.Questions])

    p.UpdatedAt = utc_now()
    db.commit()
    db.refresh(p)

    # Sync update to Google Sheets
    try:
        sheets_service.sync_paper({
            "PaperID": p.PaperID,
            "Title": p.Title,
            "PriceMinorUnits": p.PriceMinorUnits,
            "Currency": p.Currency,
            "TimeLimitMinutes": p.TimeLimitMinutes,
            "Status": p.Status,
            "Version": p.Version,
            "NegativeMarkingEnabled": p.NegativeMarkingEnabled,
            "ShowAnswerKey": p.ShowAnswerKey,
            "AllowResume": p.AllowResume,
            "AntiCheatPolicy": p.AntiCheatPolicy,
            "QuestionsJSON": p.QuestionsJSON,
            "CreatedAt": to_iso(p.CreatedAt),
            "UpdatedAt": to_iso(p.UpdatedAt)
        })
    except Exception:
        pass

    raw_q = json.loads(p.QuestionsJSON or "[]")
    questions = [Question(**q) for q in raw_q]
    return PaperDetailAdmin(
        PaperID=p.PaperID,
        Title=p.Title,
        PriceMinorUnits=p.PriceMinorUnits,
        Currency=p.Currency,
        TimeLimitMinutes=p.TimeLimitMinutes,
        Status=p.Status,
        Version=p.Version,
        NegativeMarkingEnabled=p.NegativeMarkingEnabled,
        ShowAnswerKey=p.ShowAnswerKey,
        AllowResume=p.AllowResume,
        AntiCheatPolicy=p.AntiCheatPolicy,
        Questions=questions,
        CreatedAt=to_iso(p.CreatedAt),
        UpdatedAt=to_iso(p.UpdatedAt)
    )

@router.post("/paper/{paper_id}/publish")
def publish_paper(
    paper_id: str,
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Validates and publishes a DRAFT paper making it publicly available."""
    p = db.query(PaperModel).filter(PaperModel.PaperID == paper_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paper not found.")
    if p.Status == "PUBLISHED":
        return {"status": "already_published", "paper_id": paper_id}

    # Strict Publishing Validation (Section 71)
    raw_q = json.loads(p.QuestionsJSON or "[]")
    if not raw_q or len(raw_q) == 0:
        raise HTTPException(status_code=400, detail="Cannot publish a paper without questions.")

    try:
        questions = [Question(**q) for q in raw_q]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Question validation error: {e}")

    p.Status = "PUBLISHED"
    p.UpdatedAt = utc_now()
    db.commit()

    # Sync to Google Sheets
    try:
        sheets_service.sync_paper({
            "PaperID": p.PaperID,
            "Title": p.Title,
            "PriceMinorUnits": p.PriceMinorUnits,
            "Currency": p.Currency,
            "TimeLimitMinutes": p.TimeLimitMinutes,
            "Status": "PUBLISHED",
            "Version": p.Version,
            "NegativeMarkingEnabled": p.NegativeMarkingEnabled,
            "ShowAnswerKey": p.ShowAnswerKey,
            "AllowResume": p.AllowResume,
            "AntiCheatPolicy": p.AntiCheatPolicy,
            "QuestionsJSON": p.QuestionsJSON,
            "CreatedAt": to_iso(p.CreatedAt),
            "UpdatedAt": to_iso(p.UpdatedAt)
        })
    except Exception:
        pass

    return {"status": "published", "paper_id": paper_id, "version": p.Version}

@router.post("/paper/{paper_id}/archive")
def archive_paper(
    paper_id: str,
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Archives an active paper, hiding it from public store."""
    p = db.query(PaperModel).filter(PaperModel.PaperID == paper_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paper not found.")

    p.Status = "ARCHIVED"
    p.UpdatedAt = utc_now()
    db.commit()

    # Sync to Google Sheets
    try:
        sheets_service.sync_paper({
            "PaperID": p.PaperID,
            "Title": p.Title,
            "PriceMinorUnits": p.PriceMinorUnits,
            "Currency": p.Currency,
            "TimeLimitMinutes": p.TimeLimitMinutes,
            "Status": "ARCHIVED",
            "Version": p.Version,
            "NegativeMarkingEnabled": p.NegativeMarkingEnabled,
            "ShowAnswerKey": p.ShowAnswerKey,
            "AllowResume": p.AllowResume,
            "AntiCheatPolicy": p.AntiCheatPolicy,
            "QuestionsJSON": p.QuestionsJSON,
            "CreatedAt": to_iso(p.CreatedAt),
            "UpdatedAt": to_iso(p.UpdatedAt)
        })
    except Exception:
        pass

    return {"status": "archived", "paper_id": paper_id}

@router.delete("/papers/{paper_id}")
def delete_paper(
    paper_id: str,
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Permanently deletes a paper. Blocked if active (non-completed) attempts exist."""
    p = db.query(PaperModel).filter(PaperModel.PaperID == paper_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paper not found.")

    # Guard: do not delete if there are in-progress attempts
    active_attempts = db.query(AttemptModel).filter(
        AttemptModel.PaperID == paper_id,
        AttemptModel.Status.in_(["PAID", "STARTED"])
    ).count()
    if active_attempts > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete paper with {active_attempts} active attempt(s). Archive it instead."
        )

    db.delete(p)
    db.commit()

    # Best-effort Sheets notification
    try:
        sheets_service.sync_paper({
            "PaperID": paper_id,
            "Title": f"[DELETED] {p.Title}",
            "PriceMinorUnits": p.PriceMinorUnits,
            "Currency": p.Currency,
            "TimeLimitMinutes": p.TimeLimitMinutes,
            "Status": "DELETED",
            "Version": p.Version,
            "NegativeMarkingEnabled": p.NegativeMarkingEnabled,
            "ShowAnswerKey": p.ShowAnswerKey,
            "AllowResume": p.AllowResume,
            "AntiCheatPolicy": p.AntiCheatPolicy,
            "QuestionsJSON": "[]",
            "CreatedAt": to_iso(p.CreatedAt),
            "UpdatedAt": to_iso(utc_now())
        })
    except Exception:
        pass

    return {"status": "deleted", "paper_id": paper_id}

@router.post("/paper/{paper_id}/duplicate", response_model=PaperDetailAdmin)
def duplicate_paper(
    paper_id: str,
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Clones a paper into a new editable DRAFT with incremented version."""
    p = db.query(PaperModel).filter(PaperModel.PaperID == paper_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Paper not found.")

    new_paper_id = f"pap_{uuid.uuid4().hex[:10]}"
    now = utc_now()
    new_paper = PaperModel(
        PaperID=new_paper_id,
        Title=f"{p.Title} (Copy)",
        PriceMinorUnits=p.PriceMinorUnits,
        Currency=p.Currency,
        TimeLimitMinutes=p.TimeLimitMinutes,
        Status="DRAFT",
        Version=p.Version + 1,
        NegativeMarkingEnabled=p.NegativeMarkingEnabled,
        ShowAnswerKey=p.ShowAnswerKey,
        AllowResume=p.AllowResume,
        AntiCheatPolicy=p.AntiCheatPolicy,
        QuestionsJSON=p.QuestionsJSON,
        CreatedAt=now,
        UpdatedAt=now
    )
    db.add(new_paper)
    db.commit()
    db.refresh(new_paper)

    raw_q = json.loads(new_paper.QuestionsJSON or "[]")
    questions = [Question(**q) for q in raw_q]
    return PaperDetailAdmin(
        PaperID=new_paper.PaperID,
        Title=new_paper.Title,
        PriceMinorUnits=new_paper.PriceMinorUnits,
        Currency=new_paper.Currency,
        TimeLimitMinutes=new_paper.TimeLimitMinutes,
        Status=new_paper.Status,
        Version=new_paper.Version,
        NegativeMarkingEnabled=new_paper.NegativeMarkingEnabled,
        ShowAnswerKey=new_paper.ShowAnswerKey,
        AllowResume=new_paper.AllowResume,
        AntiCheatPolicy=new_paper.AntiCheatPolicy,
        Questions=questions,
        CreatedAt=to_iso(new_paper.CreatedAt),
        UpdatedAt=to_iso(new_paper.UpdatedAt)
    )

@router.get("/attempts")
def list_attempts(
    admin: AdminSessionModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Returns assessment attempt records and grading results for provider reporting."""
    attempts = db.query(AttemptModel).order_by(AttemptModel.Timestamp.desc()).limit(100).all()
    results = []
    for a in attempts:
        results.append({
            "AttemptID": a.AttemptID,
            "OrderID": a.OrderID,
            "PaymentID": a.PaymentID,
            "Name": a.Name,
            "StudentIdentifier": a.StudentIdentifier,
            "PaperID": a.PaperID,
            "PaperVersion": a.PaperVersion,
            "Status": a.Status,
            "Score": a.Score,
            "MaxMarks": a.MaxMarks,
            "StrikeCount": a.StrikeCount,
            "StartedAt": to_iso(a.StartedAt),
            "CompletedAt": to_iso(a.CompletedAt),
            "Timestamp": to_iso(a.Timestamp)
        })
    return results

