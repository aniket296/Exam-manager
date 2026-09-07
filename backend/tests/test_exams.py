import json
from datetime import timedelta
from backend.models import PaperModel, AttemptModel
from backend.services.token_service import generate_exam_credential
from backend.utils.time import utc_now, to_iso

def setup_test_attempt(db_session, anti_cheat="AUTO_SUBMIT_ON_3"):
    q_data = [
        {
            "QuestionID": "Q1",
            "QuestionText": "What is 5 × 5?",
            "Type": "MCQ",
            "Options": [
                {"OptionID": "OPT_A", "Text": "20"},
                {"OptionID": "OPT_B", "Text": "25"},
                {"OptionID": "OPT_C", "Text": "30"}
            ],
            "CorrectAnswer": "OPT_B",
            "MarksCorrect": 4.0,
            "MarksNegative": 1.0
        },
        {
            "QuestionID": "Q2",
            "QuestionText": "Name the largest ocean on Earth.",
            "Type": "Text",
            "Options": [],
            "CorrectAnswer": "pacific,pacific ocean",
            "MarksCorrect": 4.0,
            "MarksNegative": 0.0
        }
    ]
    paper = PaperModel(
        PaperID="pap_exam_test",
        Title="General Quiz",
        PriceMinorUnits=1000,
        Currency="INR",
        TimeLimitMinutes=15,
        Status="PUBLISHED",
        Version=1,
        NegativeMarkingEnabled=True,
        ShowAnswerKey=True,
        AntiCheatPolicy=anti_cheat,
        QuestionsJSON=json.dumps(q_data),
        CreatedAt=utc_now(),
        UpdatedAt=utc_now()
    )
    db_session.add(paper)
    db_session.commit()

    raw_token, token_hash, _ = generate_exam_credential()
    now = utc_now()
    attempt = AttemptModel(
        AttemptID="att_test_123",
        OrderID="ord_test_123",
        PaymentID="pay_test_123",
        Name="Aarav Patel",
        PaperID=paper.PaperID,
        PaperVersion=1,
        AmountMinorUnits=1000,
        Currency="INR",
        Status="PAID",
        AttemptTokenHash=token_hash,
        TokenCreatedAt=now,
        TokenExpiresAt=now + timedelta(hours=24),
        Timestamp=now
    )
    db_session.add(attempt)
    db_session.commit()
    return attempt, raw_token

def test_exam_start_and_randomization_freeze(client, db_session):
    attempt, token = setup_test_attempt(db_session)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Start Exam
    res = client.get("/exam", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["AttemptID"] == attempt.AttemptID
    assert len(data["Questions"]) == 2
    
    # Assert NO answers or correct answer metadata in response
    for q in data["Questions"]:
        assert "CorrectAnswer" not in q

    first_q_order = [q["QuestionID"] for q in data["Questions"]]
    first_opt_order = [opt["OptionID"] for opt in data["Questions"][0]["Options"]]

    # 2. Reload/Resume Exam: Must preserve EXACT same frozen order
    res_reload = client.get("/exam", headers=headers)
    assert res_reload.status_code == 200
    reload_data = res_reload.json()
    reload_q_order = [q["QuestionID"] for q in reload_data["Questions"]]
    reload_opt_order = [opt["OptionID"] for opt in reload_data["Questions"][0]["Options"]]

    assert first_q_order == reload_q_order
    assert first_opt_order == reload_opt_order

def test_anti_cheat_strike_policy(client, db_session):
    attempt, token = setup_test_attempt(db_session, anti_cheat="AUTO_SUBMIT_ON_3")
    headers = {"Authorization": f"Bearer {token}"}

    # Start exam first
    client.get("/exam", headers=headers)

    # Strike 1: Warning
    res1 = client.post("/exam/event", json={"EventType": "TAB_HIDDEN"}, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["StrikeCount"] == 1
    assert res1.json()["ActionTaken"] == "WARNING"

    # Strike 2: Warning
    res2 = client.post("/exam/event", json={"EventType": "WINDOW_BLUR"}, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["StrikeCount"] == 2
    assert res2.json()["ActionTaken"] == "WARNING"

    # Strike 3: Auto-submit threshold triggered
    res3 = client.post("/exam/event", json={"EventType": "FULLSCREEN_EXIT"}, headers=headers)
    assert res3.status_code == 200
    assert res3.json()["StrikeCount"] == 3
    assert res3.json()["ActionTaken"] == "AUTO_SUBMITTED"

def test_exam_submission_and_idempotency(client, db_session):
    attempt, token = setup_test_attempt(db_session)
    headers = {"Authorization": f"Bearer {token}"}

    # Start exam
    client.get("/exam", headers=headers)

    # Submit answers: Q1 correct ("OPT_B"), Q2 correct ("Pacific Ocean" normalized)
    submit_payload = {
        "Answers": {
            "Q1": "OPT_B",
            "Q2": "  Pacific   Ocean  "
        }
    }
    res = client.post("/exam/submit", json=submit_payload, headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["Score"] == 8.0  # 4 + 4
    assert res_data["CorrectCount"] == 2
    assert res_data["WrongCount"] == 0

    # Idempotent re-submission (e.g. user double-clicked)
    res_dup = client.post("/exam/submit", json=submit_payload, headers=headers)
    assert res_dup.status_code == 200
    assert res_dup.json()["Score"] == 8.0

