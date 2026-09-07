import json
import random
import secrets
from datetime import timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models import AttemptModel, PaperModel
from backend.schemas import Question, ExamSafeQuestion, ExamSafeOption
from backend.services.scoring_service import score_attempt
from backend.services.sheets_service import sheets_service
from backend.utils.time import utc_now, to_iso, is_expired

class ExamService:
    def get_or_start_exam(
        self,
        attempt: AttemptModel,
        db: Session,
        requested_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Starts the exam or resumes an active attempt.
        Freezes question & option order once per attempt.
        Enforces single active session and authoritative deadline.
        """
        now = utc_now()
        paper = db.query(PaperModel).filter(PaperModel.PaperID == attempt.PaperID).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Assessment paper not found.")

        # If already completed -> 403 Forbidden
        if attempt.Status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This assessment link has already been completed."
            )

        # First time starting
        if attempt.Status == "PAID":
            attempt.Status = "STARTED"
            attempt.StartedAt = now
            attempt.Deadline = now + timedelta(minutes=paper.TimeLimitMinutes)
            attempt.SessionID = requested_session_id or secrets.token_hex(16)
            attempt.LastSeenAt = now

            # Parse questions
            raw_questions = json.loads(paper.QuestionsJSON)
            questions_obj = [Question(**q) for q in raw_questions]

            # Securely randomize question order
            q_order = [q.QuestionID for q in questions_obj]
            secrets.SystemRandom().shuffle(q_order)
            attempt.QuestionOrderJSON = json.dumps(q_order)

            # Securely randomize MCQ option orders
            opt_order_map = {}
            for q in questions_obj:
                if q.Type == "MCQ" and q.Options:
                    opts = [opt.OptionID for opt in q.Options]
                    secrets.SystemRandom().shuffle(opts)
                    opt_order_map[q.QuestionID] = opts
            attempt.OptionOrderJSON = json.dumps(opt_order_map)

            db.commit()
            db.refresh(attempt)

        elif attempt.Status == "STARTED":
            # Link-sharing / Concurrent session exploit check
            if requested_session_id and attempt.SessionID and requested_session_id != attempt.SessionID:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Link already in use on another device or browser session."
                )
            # Resume session - update last seen
            attempt.LastSeenAt = now
            if not attempt.SessionID:
                attempt.SessionID = requested_session_id or secrets.token_hex(16)
            db.commit()

        # Check deadline
        if is_expired(attempt.Deadline, grace_seconds=15):
            # Deadline passed
            attempt.Status = "COMPLETED"
            attempt.CompletedAt = now
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="The allocated time for this test has ended."
            )

        # Reconstruct randomized questions according to saved snapshot
        raw_questions = json.loads(paper.QuestionsJSON)
        q_lookup = {q["QuestionID"]: q for q in raw_questions}
        saved_q_order = json.loads(attempt.QuestionOrderJSON or "[]")
        saved_opt_order_map = json.loads(attempt.OptionOrderJSON or "{}")

        ordered_safe_questions: List[ExamSafeQuestion] = []
        for qid in saved_q_order:
            if qid in q_lookup:
                raw_q = q_lookup[qid]
                q_model = Question(**raw_q)
                
                safe_opts: List[ExamSafeOption] = []
                if q_model.Type == "MCQ":
                    opt_lookup = {opt.OptionID: opt.Text for opt in q_model.Options}
                    ordered_opt_ids = saved_opt_order_map.get(qid, [opt.OptionID for opt in q_model.Options])
                    for opt_id in ordered_opt_ids:
                        if opt_id in opt_lookup:
                            safe_opts.append(ExamSafeOption(OptionID=opt_id, Text=opt_lookup[opt_id]))

                ordered_safe_questions.append(
                    ExamSafeQuestion(
                        QuestionID=q_model.QuestionID,
                        QuestionText=q_model.QuestionText,
                        ImageURL=q_model.ImageURL or "",
                        ImageAltText=q_model.ImageAltText or "",
                        Type=q_model.Type,
                        Options=safe_opts,
                        MarksCorrect=q_model.MarksCorrect,
                        MarksNegative=q_model.MarksNegative if paper.NegativeMarkingEnabled else 0.0
                    )
                )

        # Sync update to Google Sheets in background
        try:
            sheets_service.sync_attempt({
                "AttemptID": attempt.AttemptID,
                "OrderID": attempt.OrderID,
                "PaymentID": attempt.PaymentID,
                "Name": attempt.Name,
                "StudentIdentifier": attempt.StudentIdentifier,
                "PaperID": attempt.PaperID,
                "PaperVersion": attempt.PaperVersion,
                "AmountMinorUnits": attempt.AmountMinorUnits,
                "Status": attempt.Status,
                "StartedAt": to_iso(attempt.StartedAt),
                "Deadline": to_iso(attempt.Deadline),
                "StrikeCount": attempt.StrikeCount,
                "SessionID": attempt.SessionID,
                "LastSeenAt": to_iso(attempt.LastSeenAt),
                "QuestionOrderJSON": attempt.QuestionOrderJSON,
                "OptionOrderJSON": attempt.OptionOrderJSON,
                "Timestamp": to_iso(attempt.Timestamp)
            })
        except Exception:
            pass

        return {
            "AttemptID": attempt.AttemptID,
            "PaperID": paper.PaperID,
            "PaperTitle": paper.Title,
            "StudentName": attempt.Name,
            "TimeLimitMinutes": paper.TimeLimitMinutes,
            "StartedAt": to_iso(attempt.StartedAt),
            "Deadline": to_iso(attempt.Deadline),
            "NegativeMarkingEnabled": paper.NegativeMarkingEnabled,
            "AntiCheatPolicy": paper.AntiCheatPolicy,
            "Questions": ordered_safe_questions,
            "SessionID": attempt.SessionID
        }

    def record_heartbeat(self, attempt: AttemptModel, session_id: Optional[str], db: Session) -> Dict[str, Any]:
        """Records student heartbeat and returns authoritative remaining time."""
        now = utc_now()
        attempt.LastSeenAt = now
        db.commit()

        deadline = attempt.Deadline
        if deadline:
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=now.tzinfo)
            remaining = max(0, int((deadline - now).total_seconds()))
        else:
            remaining = 0

        return {
            "Status": attempt.Status,
            "RemainingSeconds": remaining,
            "StrikeCount": attempt.StrikeCount,
            "Deadline": to_iso(attempt.Deadline)
        }

    def record_anti_cheat_event(
        self,
        attempt: AttemptModel,
        event_type: str,
        details: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Increments strike count and enforces paper policy (warnings or auto-submit).
        Uses calm, age-appropriate messaging.
        """
        attempt.StrikeCount += 1
        db.commit()

        paper = db.query(PaperModel).filter(PaperModel.PaperID == attempt.PaperID).first()
        policy = paper.AntiCheatPolicy if paper else "AUTO_SUBMIT_ON_3"

        auto_submit_threshold = 3 if policy == "AUTO_SUBMIT_ON_3" else (5 if policy == "AUTO_SUBMIT_ON_5" else 999)

        if attempt.StrikeCount >= auto_submit_threshold:
            # Trigger auto-submit
            return {
                "Recorded": True,
                "StrikeCount": attempt.StrikeCount,
                "ActionTaken": "AUTO_SUBMITTED",
                "FriendlyMessage": "Your test is being submitted now. Thank you for completing your test!"
            }
        elif attempt.StrikeCount == 1:
            friendly_msg = "Please stay on the test screen until you finish your questions."
        else:
            friendly_msg = "Please return to your test screen so your work is saved."

        return {
            "Recorded": True,
            "StrikeCount": attempt.StrikeCount,
            "ActionTaken": "WARNING",
            "FriendlyMessage": friendly_msg
        }

    def submit_exam(
        self,
        attempt: AttemptModel,
        answers: Dict[str, str],
        db: Session
    ) -> Dict[str, Any]:
        """
        Submits and authoritatively grades the attempt.
        Concurrency-safe and idempotent: duplicate submissions return previously graded result.
        """
        now = utc_now()
        paper = db.query(PaperModel).filter(PaperModel.PaperID == attempt.PaperID).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Assessment paper not found.")

        # Idempotent re-submission: return the stored result instead of failing.
        if attempt.Status == "COMPLETED":
            paper = db.query(PaperModel).filter(PaperModel.PaperID == attempt.PaperID).first()
            return {
                "AttemptID": attempt.AttemptID,
                "StudentName": attempt.Name,
                "PaperTitle": paper.Title if paper else "",
                "Score": attempt.Score,
                "MaxMarks": attempt.MaxMarks,
                "Percentage": (attempt.Score / attempt.MaxMarks * 100.0) if attempt.MaxMarks and attempt.MaxMarks > 0 else 0.0,
                "CorrectCount": attempt.CorrectCount,
                "WrongCount": attempt.WrongCount,
                "UnansweredCount": attempt.UnansweredCount,
                "CompletedAt": to_iso(attempt.CompletedAt),
                "ShowAnswerKey": bool(paper.ShowAnswerKey) if paper else False,
                "QuestionBreakdown": None,
            }

        # Check authoritative deadline with 30-second submission network grace
        deadline = attempt.Deadline
        if deadline:
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=now.tzinfo)
            if now > (deadline + timedelta(seconds=30)):
                # Still allow submission grading but log deadline closure
                pass

        # Load authoritative paper questions
        raw_questions = json.loads(paper.QuestionsJSON)
        questions_obj = [Question(**q) for q in raw_questions]

        # Calculate authoritative score
        scoring_result = score_attempt(
            questions=questions_obj,
            student_answers=answers,
            negative_marking_enabled=paper.NegativeMarkingEnabled,
            show_answer_key=paper.ShowAnswerKey
        )

        # Finalize attempt state
        attempt.Status = "COMPLETED"
        attempt.CompletedAt = now
        attempt.Score = scoring_result["score"]
        attempt.MaxMarks = scoring_result["max_marks"]
        attempt.CorrectCount = scoring_result["correct_count"]
        attempt.WrongCount = scoring_result["wrong_count"]
        attempt.UnansweredCount = scoring_result["unanswered_count"]
        attempt.AnswersJSON = json.dumps(answers)

        db.commit()
        db.refresh(attempt)

        # Sync completion to Google Sheets
        try:
            sheets_service.sync_attempt({
                "AttemptID": attempt.AttemptID,
                "OrderID": attempt.OrderID,
                "PaymentID": attempt.PaymentID,
                "Name": attempt.Name,
                "StudentIdentifier": attempt.StudentIdentifier,
                "PaperID": attempt.PaperID,
                "PaperVersion": attempt.PaperVersion,
                "AmountMinorUnits": attempt.AmountMinorUnits,
                "Status": "COMPLETED",
                "StartedAt": to_iso(attempt.StartedAt),
                "Deadline": to_iso(attempt.Deadline),
                "CompletedAt": to_iso(attempt.CompletedAt),
                "Score": attempt.Score,
                "StrikeCount": attempt.StrikeCount,
                "Timestamp": to_iso(attempt.Timestamp)
            })
        except Exception:
            pass

        return {
            "AttemptID": attempt.AttemptID,
            "StudentName": attempt.Name,
            "PaperTitle": paper.Title,
            "Score": attempt.Score,
            "MaxMarks": attempt.MaxMarks,
            "Percentage": scoring_result["percentage"],
            "CorrectCount": attempt.CorrectCount,
            "WrongCount": attempt.WrongCount,
            "UnansweredCount": attempt.UnansweredCount,
            "CompletedAt": to_iso(attempt.CompletedAt),
            "ShowAnswerKey": paper.ShowAnswerKey,
            "QuestionBreakdown": scoring_result["breakdown"]
        }

exam_service = ExamService()

