"""
Suite 2: State Machine & Payment Security (Integration Tests)
Focus: Order lifecycle, link-sharing exploit prevention, double submission blocking, webhook signature tampering.
"""
import pytest
from backend.models import OrderModel, AttemptModel
from tests.fixtures.mock_razorpay import (
    generate_mock_webhook_payload, generate_webhook_signature,
    generate_tampered_webhook_signature
)

# --- 1. Lifecycle Transition Tests ---
def test_complete_lifecycle_transitions(client, db_session, sample_paper):
    # Step A: Create mock order
    create_res = client.post("/payments/create-order", json={
        "PaperID": sample_paper.PaperID,
        "StudentName": "Tara Joshi",
        "StudentIdentifier": "Class 7-A"
    })
    assert create_res.status_code == 200
    order_id = create_res.json()["OrderID"]

    order_db = db_session.query(OrderModel).filter(OrderModel.OrderID == order_id).first()
    assert order_db.Status == "CREATED"

    # Step B: Trigger mock webhook payment.captured -> transitions to PAID
    payment_id = f"pay_{order_id}"
    payload, raw_body = generate_mock_webhook_payload(
        event_type="payment.captured",
        order_id=order_id,
        payment_id=payment_id,
        amount=sample_paper.PriceMinorUnits
    )
    valid_sig = generate_webhook_signature(raw_body)

    wh_res = client.post(
        "/payments/webhook",
        content=raw_body,
        headers={"x-razorpay-signature": valid_sig, "content-type": "application/json"}
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] == "success"

    attempt_db = db_session.query(AttemptModel).filter(AttemptModel.OrderID == order_id).first()
    assert attempt_db is not None
    assert attempt_db.Status == "PAID"

    # Step C: First student access (GET /paper/...) -> transitions from PAID to STARTED
    get_res = client.get(
        f"/paper/{sample_paper.PaperID}/{payment_id}",
        headers={"X-Session-ID": "session_device_primary"}
    )
    assert get_res.status_code == 200

    db_session.refresh(attempt_db)
    assert attempt_db.Status == "STARTED"
    assert attempt_db.StartedAt is not None
    assert attempt_db.Deadline is not None

    # Step D: Submission -> transitions from STARTED to COMPLETED
    sub_res = client.post(f"/submit/{sample_paper.PaperID}/{payment_id}", json={
        "Answers": {
            "Q101": "OPT_B",
            "Q102": "USA",
            "Q103": "OPT_Y"
        }
    })
    assert sub_res.status_code == 200
    assert sub_res.json()["Score"] == 10.0

    db_session.refresh(attempt_db)
    assert attempt_db.Status == "COMPLETED"
    assert attempt_db.CompletedAt is not None
    assert attempt_db.Score == 10.0

# --- 2. Link-Sharing Exploit Prevention ---
def test_link_sharing_and_unauthorized_access(client, db_session, sample_paper):
    # Setup attempt in STARTED state with an active session
    create_res = client.post("/payments/create-order", json={
        "PaperID": sample_paper.PaperID,
        "StudentName": "Vikram Seth"
    })
    order_id = create_res.json()["OrderID"]
    payment_id = f"pay_{order_id}"

    # Capture payment
    payload, raw_body = generate_mock_webhook_payload(order_id=order_id, payment_id=payment_id)
    client.post(
        "/payments/webhook",
        content=raw_body,
        headers={"x-razorpay-signature": generate_webhook_signature(raw_body)}
    )

    # Primary user starts test with session "session_alpha"
    client.get(
        f"/paper/{sample_paper.PaperID}/{payment_id}",
        headers={"X-Session-ID": "session_alpha"}
    )

    # Exploiter attempts concurrent access from another device with session "session_beta" -> Expect 403
    concurrent_res = client.get(
        f"/paper/{sample_paper.PaperID}/{payment_id}",
        headers={"X-Session-ID": "session_beta"}
    )
    assert concurrent_res.status_code == 403
    assert "in use" in concurrent_res.json()["detail"].lower()

    # Complete test
    client.post(f"/submit/{sample_paper.PaperID}/{payment_id}", json={"Answers": {"Q101": "OPT_B"}})

    # Attempt access using COMPLETED payment token -> Expect 403 Forbidden
    completed_res = client.get(
        f"/paper/{sample_paper.PaperID}/{payment_id}",
        headers={"X-Session-ID": "session_alpha"}
    )
    assert completed_res.status_code == 403

    # Attempt to access using unpaid / invalid payment token -> Expect 401 or 404
    invalid_res = client.get(f"/paper/{sample_paper.PaperID}/nonexistent_payment_token")
    assert invalid_res.status_code in [401, 404]

# --- 3. Double Submission Prevention ---
def test_double_submission_prevention(client, db_session, sample_paper):
    create_res = client.post("/payments/create-order", json={
        "PaperID": sample_paper.PaperID,
        "StudentName": "Neha Roy"
    })
    order_id = create_res.json()["OrderID"]
    payment_id = f"pay_{order_id}"

    payload, raw_body = generate_mock_webhook_payload(order_id=order_id, payment_id=payment_id)
    client.post(
        "/payments/webhook",
        content=raw_body,
        headers={"x-razorpay-signature": generate_webhook_signature(raw_body)}
    )

    # Start test
    client.get(f"/paper/{sample_paper.PaperID}/{payment_id}")

    # First submission -> 200 OK
    res_1 = client.post(f"/submit/{sample_paper.PaperID}/{payment_id}", json={"Answers": {"Q101": "OPT_B"}})
    assert res_1.status_code == 200

    # Second submission -> Idempotently returns the stored result
    res_2 = client.post(f"/submit/{sample_paper.PaperID}/{payment_id}", json={"Answers": {"Q101": "OPT_B"}})
    assert res_2.status_code == 200
    assert res_2.json()["Score"] == res_1.json()["Score"]

# --- 4. Webhook Signature Tampering ---
def test_webhook_signature_tampering(client):
    payload, raw_body = generate_mock_webhook_payload()
    tampered_sig = generate_tampered_webhook_signature(raw_body)

    # Tampered signature -> 400 Bad Request
    res = client.post(
        "/payments/webhook",
        content=raw_body,
        headers={"x-razorpay-signature": tampered_sig, "content-type": "application/json"}
    )
    assert res.status_code == 400
    assert "signature" in res.json()["detail"].lower()
