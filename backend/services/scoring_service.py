import re
from typing import Dict, List, Any, Tuple
from backend.schemas import Question, QuestionResultItem

def normalize_text_answer(text: str) -> str:
    """Normalizes text answer: lowercase, strip, collapse consecutive whitespace."""
    if not text:
        return ""
    # Collapse multiple whitespace characters into a single space
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return cleaned

def evaluate_question(
    q: Question,
    student_ans: str,
    negative_marking_enabled: bool
) -> Tuple[bool, bool, float]:
    """
    Evaluates an individual question.
    Returns:
        (is_answered, is_correct, marks_awarded)
    """
    if not student_ans or str(student_ans).strip() == "":
        return False, False, 0.0

    student_ans_str = str(student_ans).strip()

    if q.Type == "MCQ":
        # MCQ evaluates OptionID equality
        if student_ans_str == q.CorrectAnswer:
            return True, True, float(q.MarksCorrect)
        else:
            neg_marks = float(q.MarksNegative) if negative_marking_enabled else 0.0
            return True, False, -neg_marks

    elif q.Type == "Text":
        # Text normalization and alias matching
        normalized_student = normalize_text_answer(student_ans_str)
        # Aliases are split by comma
        valid_aliases = [normalize_text_answer(a) for a in q.CorrectAnswer.split(",") if a.strip()]
        if normalized_student in valid_aliases:
            return True, True, float(q.MarksCorrect)
        else:
            neg_marks = float(q.MarksNegative) if negative_marking_enabled else 0.0
            return True, False, -neg_marks

    return False, False, 0.0

def score_attempt(
    questions: List[Question],
    student_answers: Dict[str, str],
    negative_marking_enabled: bool,
    show_answer_key: bool
) -> Dict[str, Any]:
    """
    Authoritative backend grading engine.
    Calculates score, counts, and breakdown.
    """
    total_score = 0.0
    max_marks = 0.0
    correct_count = 0
    wrong_count = 0
    unanswered_count = 0
    breakdown: List[QuestionResultItem] = []

    for q in questions:
        max_marks += float(q.MarksCorrect)
        ans = student_answers.get(q.QuestionID, "")
        is_answered, is_correct, marks = evaluate_question(q, ans, negative_marking_enabled)

        if not is_answered:
            unanswered_count += 1
        elif is_correct:
            correct_count += 1
        else:
            wrong_count += 1

        total_score += marks

        breakdown.append(
            QuestionResultItem(
                QuestionID=q.QuestionID,
                QuestionText=q.QuestionText,
                Type=q.Type,
                StudentAnswer=ans if ans else None,
                IsCorrect=is_correct,
                MarksAwarded=marks,
                CorrectAnswer=q.CorrectAnswer if show_answer_key else None
            )
        )

    # Round score to 2 decimal places
    total_score = round(total_score, 2)
    percentage = round((total_score / max_marks * 100) if max_marks > 0 else 0.0, 1)

    return {
        "score": total_score,
        "max_marks": max_marks,
        "percentage": percentage,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "unanswered_count": unanswered_count,
        "breakdown": breakdown
    }

