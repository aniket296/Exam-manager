import json
from backend.models import PaperModel
from backend.utils.time import utc_now

def test_admin_login_and_paper_lifecycle(client):
    # 1. Admin login with wrong password
    res = client.post("/admin/login", json={"Password": "WrongPassword!"})
    assert res.status_code == 401

    # 2. Admin login with correct default password
    res = client.post("/admin/login", json={"Password": "Admin@12345"})
    assert res.status_code == 200
    token = res.json()["Token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Draft Paper
    paper_payload = {
        "Title": "Primary Science Standard 6",
        "PriceMinorUnits": 2500,
        "Currency": "INR",
        "TimeLimitMinutes": 15,
        "NegativeMarkingEnabled": True,
        "ShowAnswerKey": True,
        "AllowResume": True,
        "AntiCheatPolicy": "AUTO_SUBMIT_ON_3",
        "Questions": [
            {
                "QuestionID": "Q1",
                "QuestionText": "Which gas do plants absorb during photosynthesis?",
                "ImageURL": "",
                "ImageAltText": "",
                "Type": "MCQ",
                "Options": [
                    {"OptionID": "OPT1", "Text": "Oxygen"},
                    {"OptionID": "OPT2", "Text": "Carbon Dioxide"},
                    {"OptionID": "OPT3", "Text": "Nitrogen"}
                ],
                "CorrectAnswer": "OPT2",
                "MarksCorrect": 4.0,
                "MarksNegative": 1.0
            }
        ]
    }
    res = client.post("/admin/create-paper", json=paper_payload, headers=headers)
    assert res.status_code == 200
    paper_id = res.json()["PaperID"]
    assert res.json()["Status"] == "DRAFT"

    # 4. Confirm it does NOT appear in public papers listing while DRAFT
    res = client.get("/papers")
    assert res.status_code == 200
    public_papers = [p["PaperID"] for p in res.json()]
    assert paper_id not in public_papers

    # 5. Publish Paper
    res = client.post(f"/admin/paper/{paper_id}/publish", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "published"

    # 6. Verify it now appears in public papers listing without CorrectAnswer
    res = client.get("/papers")
    assert res.status_code == 200
    found = [p for p in res.json() if p["PaperID"] == paper_id]
    assert len(found) == 1
    assert found[0]["Title"] == "Primary Science Standard 6"
    assert "CorrectAnswer" not in found[0]

def test_paper_validation_rules(client):
    res = client.post("/admin/login", json={"Password": "Admin@12345"})
    headers = {"Authorization": f"Bearer {res.json()['Token']}"}

    # Reject duplicate question IDs
    invalid_payload = {
        "Title": "Bad Paper",
        "PriceMinorUnits": 1000,
        "Currency": "INR",
        "TimeLimitMinutes": 10,
        "Questions": [
            {
                "QuestionID": "Q_DUP",
                "QuestionText": "First question",
                "Type": "MCQ",
                "Options": [{"OptionID": "O1", "Text": "A"}, {"OptionID": "O2", "Text": "B"}],
                "CorrectAnswer": "O1",
                "MarksCorrect": 2.0,
                "MarksNegative": 0.0
            },
            {
                "QuestionID": "Q_DUP",
                "QuestionText": "Second question duplicate id",
                "Type": "MCQ",
                "Options": [{"OptionID": "O1", "Text": "A"}, {"OptionID": "O2", "Text": "B"}],
                "CorrectAnswer": "O1",
                "MarksCorrect": 2.0,
                "MarksNegative": 0.0
            }
        ]
    }
    res = client.post("/admin/create-paper", json=invalid_payload, headers=headers)
    assert res.status_code == 422

