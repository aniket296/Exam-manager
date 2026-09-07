from backend.schemas import Question, OptionItem
from backend.services.scoring_service import score_attempt, normalize_text_answer

def test_normalize_text_answer():
    assert normalize_text_answer("  New   Delhi  ") == "new delhi"
    assert normalize_text_answer("DELHI") == "delhi"
    assert normalize_text_answer("") == ""

def test_scoring_engine_mcq_and_text():
    questions = [
        Question(
            QuestionID="Q1",
            QuestionText="2 + 3?",
            Type="MCQ",
            Options=[
                OptionItem(OptionID="OPT1", Text="4"),
                OptionItem(OptionID="OPT2", Text="5")
            ],
            CorrectAnswer="OPT2",
            MarksCorrect=4.0,
            MarksNegative=1.0
        ),
        Question(
            QuestionID="Q2",
            QuestionText="Capital of France?",
            Type="Text",
            Options=[],
            CorrectAnswer="paris,city of lights",
            MarksCorrect=4.0,
            MarksNegative=1.0
        ),
        Question(
            QuestionID="Q3",
            QuestionText="Unanswered question",
            Type="MCQ",
            Options=[
                OptionItem(OptionID="OPT3", Text="A"),
                OptionItem(OptionID="OPT4", Text="B")
            ],
            CorrectAnswer="OPT3",
            MarksCorrect=4.0,
            MarksNegative=1.0
        )
    ]

    # Student answers: Q1 wrong ("OPT1"), Q2 correct (" PARIS "), Q3 omitted ("")
    student_answers = {
        "Q1": "OPT1",
        "Q2": "  PARIS  "
    }

    # With negative marking enabled:
    # Q1: -1.0
    # Q2: +4.0
    # Q3: 0.0
    # Total = 3.0
    res_neg = score_attempt(
        questions=questions,
        student_answers=student_answers,
        negative_marking_enabled=True,
        show_answer_key=True
    )
    assert res_neg["score"] == 3.0
    assert res_neg["correct_count"] == 1
    assert res_neg["wrong_count"] == 1
    assert res_neg["unanswered_count"] == 1
    assert res_neg["max_marks"] == 12.0

    # With negative marking disabled:
    # Q1: 0.0 (no penalty)
    # Q2: +4.0
    # Q3: 0.0
    # Total = 4.0
    res_no_neg = score_attempt(
        questions=questions,
        student_answers=student_answers,
        negative_marking_enabled=False,
        show_answer_key=False
    )
    assert res_no_neg["score"] == 4.0
    assert res_no_neg["correct_count"] == 1
    assert res_no_neg["wrong_count"] == 1
    assert res_no_neg["unanswered_count"] == 1
    # Check that when show_answer_key is False, CorrectAnswer is None in breakdown
    for item in res_no_neg["breakdown"]:
        assert item.CorrectAnswer is None

