import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.models import get_db, PaperModel
from backend.schemas import PaperPublicSummary

router = APIRouter(prefix="/papers", tags=["Public Papers"])

@router.get("", response_model=List[PaperPublicSummary])
def list_published_papers(db: Session = Depends(get_db)):
    """
    Returns only PUBLISHED papers for the public storefront.
    Never exposes draft/archived papers, correct answers, or internal keys.
    """
    papers = db.query(PaperModel).filter(PaperModel.Status == "PUBLISHED").all()
    result = []
    for p in papers:
        questions = json.loads(p.QuestionsJSON or "[]")
        result.append(
            PaperPublicSummary(
                PaperID=p.PaperID,
                Title=p.Title,
                PriceMinorUnits=p.PriceMinorUnits,
                Currency=p.Currency,
                TimeLimitMinutes=p.TimeLimitMinutes,
                QuestionCount=len(questions),
                NegativeMarkingEnabled=p.NegativeMarkingEnabled,
                ShowAnswerKey=p.ShowAnswerKey,
                AntiCheatPolicy=p.AntiCheatPolicy
            )
        )
    return result

@router.get("/{paper_id}", response_model=PaperPublicSummary)
def get_published_paper(paper_id: str, db: Session = Depends(get_db)):
    """
    Returns public summary of a specific published assessment paper.
    """
    p = db.query(PaperModel).filter(
        PaperModel.PaperID == paper_id,
        PaperModel.Status == "PUBLISHED"
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Assessment paper not found.")

    questions = json.loads(p.QuestionsJSON or "[]")
    return PaperPublicSummary(
        PaperID=p.PaperID,
        Title=p.Title,
        PriceMinorUnits=p.PriceMinorUnits,
        Currency=p.Currency,
        TimeLimitMinutes=p.TimeLimitMinutes,
        QuestionCount=len(questions),
        NegativeMarkingEnabled=p.NegativeMarkingEnabled,
        ShowAnswerKey=p.ShowAnswerKey,
        AntiCheatPolicy=p.AntiCheatPolicy
    )

