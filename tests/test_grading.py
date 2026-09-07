"""
Suite 1: Core Backend & Grading Logic (Unit & Integration Tests)
Focus: MCQ grading, text normalization, alias matching, randomization integrity, data leakage check.
"""
import pytest
from datetime import timedelta
from backend.schemas import Question, OptionItem
from backend.services.scoring_service import score_attempt, evaluate_question, normalize_text_answer
from backend.models import AttemptModel
from backend.services.token_service import generate_exam_credential
from backend.utils.time import utc_now

# --- 1. MCQ Evaluation Tests ---
def test_mcq_evaluation_correct_incorrect_unanswered():
    q = Question(
        QuestionID="Q_MCQ_1",
        QuestionText="What is 10 + 10?",
        Type="MCQ",
        Options=[
            OptionItem(OptionID="OPT1", Text="15"),
            OptionItem(OptionID="OPT2", Text="20")
        ],
        CorrectAnswer="OPT2",
        MarksCorrect=4.0,
        MarksNegative=1.0
    )

    # Correct option -> full MarksCorrect
    is_ans, is_corr, marks = evaluate_question(q, "OPT2", negative_marking_enabled=True)
    assert is_ans is True
    assert is_corr is True
    assert marks == 4.0

    # Incorrect option with negative marking -> -MarksNegative
    is_ans, is_corr, marks = evaluate_question(q, "OPT1", negative_marking_enabled=True)
    assert is_ans is True
    assert is_corr is False
    assert marks == -1.0

    # Incorrect option with negative marking disabled -> 0.0
    is_ans, is_corr, marks = evaluate_question(q, "OPT1", negative_marking_enabled=False)
    assert is_ans is True
    assert is_corr is False
    assert marks == 0.0

    # Unattempted / blank -> 0.0 without penalty
    is_ans, is_corr, marks = evaluate_question(q, "", negative_marking_enabled=True)
    assert is_ans is False
    assert is_corr is False
    assert marks == 0.0

# --- 2. Text Answer Evaluation Tests ---
def test_text_evaluation_exact_multialias_and_partial():
    q = Question(
        QuestionID="Q_TEXT_1",
        QuestionText="Name the country whose capital is Washington, D.C.",
        Type="Text",
        Options=[],
        CorrectAnswer="USA, US, United States",
        MarksCorrect=4.0,
        MarksNegative=1.0
    )

    # Exact string match (case-insensitive, trimming leading/trailing spaces)
    is_ans, is_corr, marks = evaluate_question(q, "  usa  ", negative_marking_enabled=True)
    assert is_ans is True
    assert is_corr is True
    assert marks == 4.0

    # Multi-alias matching
    is_ans, is_corr, marks = evaluate_question(q, "United States", negative_marking_enabled=True)
    assert is_ans is True
    assert is_corr is True
    assert marks == 4.0

    is_ans, is_corr, marks = evaluate_question(q, "   uS   ", negative_marking_enabled=True)
    assert is_ans is True
    assert is_corr is True
    assert marks == 4.0

    # Partial / incorrect string matching fails and applies negative marks
    is_ans, is_corr, marks = evaluate_question(q, "United States of America and Canada", negative_marking_enabled=True)
    assert is_ans is True
    assert is_corr is False
    assert marks == -1.0

    is_ans, is_corr, marks = evaluate_question(q, "UK", negative_marking_enabled=True)
    assert is_ans is True
    assert is_corr is False
    assert marks == -1.0

# --- 3. Randomization Integrity Tests ---
def test_randomization_integrity_and_mapping(client, db_session, sample_paper):
    now = utc_now()
    payment_id_1 = "pay_student_01"
    raw_token_1, token_hash_1, _ = generate_exam_credential()

    attempt_1 = AttemptModel(
        AttemptID="att_rnd_01",
        OrderID="ord_rnd_01",
        PaymentID=payment_id_1,
        Name="Student One",
        PaperID=sample_paper.PaperID,
        PaperVersion=1,
        AmountMinorUnits=sample_paper.PriceMinorUnits,
        Currency="INR",
        Status="PAID",
        AttemptTokenHash=token_hash_1,
        TokenCreatedAt=now,
        TokenExpiresAt=now + timedelta(hours=24),
        Timestamp=now
    )
    db_session.add(attempt_1)
    db_session.commit()

    # Request exam via GET /paper/{paper_id}/{payment_id}
    res_1 = client.get(f"/paper/{sample_paper.PaperID}/{payment_id_1}")
    assert res_1.status_code == 200
    paper_data_1 = res_1.json()

    # Grader mapping check: Student submits using OptionID
    # Q101 correct answer is OPT_B (8), Q102 is 'United States', Q103 is OPT_Y (Yes)
    student_submission = {
        "Answers": {
            "Q101": "OPT_B",
            "Q102": "  United   States  ",
            "Q103": "OPT_Y"
        }
    }

    submit_res = client.post(
        f"/submit/{sample_paper.PaperID}/{payment_id_1}",
        json=student_submission
    )
    assert submit_res.status_code == 200
    result_data = submit_res.json()

    # Assert accurate scoring mapped back without misalignment
    assert result_data["Score"] == 10.0  # 4 + 4 + 2
    assert result_data["CorrectCount"] == 3
    assert result_data["WrongCount"] == 0
    assert result_data["UnansweredCount"] == 0

# --- 4. Data Leakage Check ---
def test_data_leakage_check(client, db_session, sample_paper):
    now = utc_now()
    payment_id = "pay_leak_test"
    raw_token, token_hash, _ = generate_exam_credential()

    attempt = AttemptModel(
        AttemptID="att_leak_01",
        OrderID="ord_leak_01",
        PaymentID=payment_id,
        Name="Leak Inspector",
        PaperID=sample_paper.PaperID,
        PaperVersion=1,
        AmountMinorUnits=sample_paper.PriceMinorUnits,
        Currency="INR",
        Status="PAID",
        AttemptTokenHash=token_hash,
        TokenCreatedAt=now,
        TokenExpiresAt=now + timedelta(hours=24),
        Timestamp=now
    )
    db_session.add(attempt)
    db_session.commit()

    res = client.get(f"/paper/{sample_paper.PaperID}/{payment_id}")
    assert res.status_code == 200
    data = res.json()

    # Assert CorrectAnswer, MarksCorrect, and answer keys are strictly absent
    for question in data["Questions"]:
        assert "CorrectAnswer" not in question, f"Data leakage: CorrectAnswer present in {question['QuestionID']}"
        assert "MarksCorrect" not in question, f"Data leakage: MarksCorrect present in {question['QuestionID']}"
        assert "MarksNegative" not in question, f"Data leakage: MarksNegative present in {question['QuestionID']}"
        assert "answer_key" not in question
        assert "aliases" not in question

