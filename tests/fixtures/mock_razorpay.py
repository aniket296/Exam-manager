import hmac
import hashlib
import json
import secrets
from backend.config import settings
from backend.utils.hashing import hmac_sha256

def generate_mock_webhook_payload(
    event_type: str = "payment.captured",
    order_id: str = "order_test_123",
    payment_id: str = "pay_test_123",
    amount: int = 4900,
    event_id: str = None
):
    if not event_id:
        event_id = f"evt_{secrets.token_hex(8)}"

    payload = {
        "entity": "event",
        "account_id": "acc_test_123",
        "event": event_type,
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": amount,
                    "currency": "INR",
                    "status": "captured" if event_type == "payment.captured" else "failed",
                    "order_id": order_id,
                    "method": "upi",
                    "captured": True
                }
            }
        },
        "created_at": 1600000000,
        "event_id": event_id
    }
    raw_body = json.dumps(payload).encode("utf-8")
    return payload, raw_body

def generate_webhook_signature(raw_body: bytes, secret: str = None) -> str:
    """Generates valid HMAC-SHA256 signature for Razorpay webhook payload."""
    secret = secret or settings.RAZORPAY_WEBHOOK_SECRET
    return hmac_sha256(secret, raw_body)

def generate_tampered_webhook_signature(raw_body: bytes) -> str:
    """Generates invalid signature for security tampering tests."""
    return "tampered_bad_signature_" + secrets.token_hex(16)

def generate_checkout_signature(order_id: str, payment_id: str, secret: str = None) -> str:
    """Generates valid signature for checkout completion."""
    secret = secret or settings.RAZORPAY_KEY_SECRET
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac_sha256(secret, payload)

