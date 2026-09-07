import json
from backend.models import PaperModel
from backend.utils.time import utc_now
from backend.services.razorpay_service import razorpay_service

def setup_published_paper(db_session):
    q_data = [
        {
            "QuestionID": "Q1",
            "QuestionText": "What is 2 + 2?",
            "Type": "MCQ",
            "Options": [{"OptionID": "O1", "Text": "3"}, {"OptionID": "O2", "Text": "4"}],
            "CorrectAnswer": "O2",
            "MarksCorrect": 4.0,
            "MarksNegative": 1.0
        }
    ]
    p = PaperModel(
        PaperID="pap_pay_test",
        Title="Math Speed Test",
        PriceMinorUnits=19900,  # ₹199.00
        Currency="INR",
        TimeLimitMinutes=10,
        Status="PUBLISHED",
        Version=1,
        QuestionsJSON=json.dumps(q_data),
        CreatedAt=utc_now(),
        UpdatedAt=utc_now()
    )
    db_session.add(p)
    db_session.commit()
    return p

def test_payment_order_and_verification_lifecycle(client, db_session):
    paper = setup_published_paper(db_session)

    # 1. Create order
    res = client.post("/payments/create-order", json={
        "PaperID": paper.PaperID,
        "StudentName": "Rohan Sharma",
        "StudentIdentifier": "Class 6-B",
        "Contact": "9876543210"
    })
    assert res.status_code == 200
    data = res.json()
    order_id = data["OrderID"]
    assert data["AmountMinorUnits"] == 19900  # Authoritative price!
    assert data["Currency"] == "INR"

    # 2. Reject verification with bad signature
    bad_verify = client.post("/payments/verify", json={
        "OrderID": order_id,
        "PaymentID": "pay_sample123",
        "Signature": "invalid_bogus_signature"
    })
    assert bad_verify.status_code == 400

    # 3. Verify with valid simulation signature
    payment_id = "pay_valid_sim_999"
    valid_sig = f"sim_sig_{order_id}_{payment_id}"
    verify_res = client.post("/payments/verify", json={
        "OrderID": order_id,
        "PaymentID": payment_id,
        "Signature": valid_sig
    })
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["Success"] is True
    attempt_token = verify_data["AttemptToken"]
    assert len(attempt_token) > 20

    # 4. Attempt Replay Protection: Re-submitting the same payment verification must fail
    replay_res = client.post("/payments/verify", json={
        "OrderID": order_id,
        "PaymentID": payment_id,
        "Signature": valid_sig
    })
    assert replay_res.status_code == 409

def test_webhook_processing_and_idempotency(client, db_session):
    paper = setup_published_paper(db_session)
    order_res = client.post("/payments/create-order", json={
        "PaperID": paper.PaperID,
        "StudentName": "Priya Verma",
        "StudentIdentifier": "Class 7-A"
    })
    order_id = order_res.json()["OrderID"]

    event_id = "evt_razorpay_mock_12345"
    webhook_body = {
        "event_id": event_id,
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_webhook_999",
                    "order_id": order_id,
                    "amount": 19900,
                    "status": "captured"
                }
            }
        }
    }
    raw_payload = json.dumps(webhook_body).encode("utf-8")
    sig = "sim_webhook_sig_test"

    # 1. Process webhook
    res = client.post(
        "/payments/webhook",
        content=raw_payload,
        headers={"x-razorpay-signature": sig, "content-type": "application/json"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"

    # 2. Duplicate webhook must be handled idempotently
    dup_res = client.post(
        "/payments/webhook",
        content=raw_payload,
        headers={"x-razorpay-signature": sig, "content-type": "application/json"}
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["status"] == "already_processed"

