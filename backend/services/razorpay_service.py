import razorpay
import hmac
import hashlib
import logging
import secrets
from typing import Dict, Any, Optional, Tuple
from backend.config import settings
from backend.utils.hashing import hmac_sha256, secure_compare

logger = logging.getLogger(__name__)

class RazorpayService:
    def __init__(self):
        self.simulation_mode = bool(settings.RAZORPAY_SIMULATION_MODE)
        self._simulation_order_tokens: Dict[str, str] = {}
        self._webhook_tokens: Dict[str, str] = {}

        if not self.simulation_mode:
            if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
                raise RuntimeError("Razorpay credentials are required when simulation mode is disabled.")
            if not settings.RAZORPAY_WEBHOOK_SECRET:
                raise RuntimeError("Razorpay webhook secret is required when simulation mode is disabled.")
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
        else:
            self.client = None
            logger.info("Razorpay running in SIMULATION/DEMO mode.")

    def _generate_simulation_token(self, order_id: str) -> str:
        token = secrets.token_urlsafe(24)
        self._simulation_order_tokens[order_id] = token
        return token

    def generate_simulation_payment_signature(self, order_id: str, payment_id: str, token: str) -> str:
        return f"sim_sig_{order_id}_{payment_id}_{token}"

    def generate_webhook_signature(self, raw_body: bytes) -> str:
        token = secrets.token_urlsafe(24)
        digest = hashlib.sha256(raw_body).hexdigest()
        self._webhook_tokens[digest] = token
        return f"sim_webhook_sig_{digest}_{token}"

    def create_order(self, amount_minor_units: int, currency: str, receipt: str, notes: Dict[str, str]) -> Dict[str, Any]:
        """Creates a Razorpay order or simulated order."""
        if not self.simulation_mode and self.client:
            try:
                data = {
                    "amount": amount_minor_units,
                    "currency": currency,
                    "receipt": receipt,
                    "notes": notes,
                    "payment_capture": 1
                }
                return self.client.order.create(data=data)
            except Exception as e:
                logger.error(f"Razorpay order creation error: {e}")
                raise e

        sim_order_id = f"order_sim_{secrets.token_hex(10)}"
        simulation_token = self._generate_simulation_token(sim_order_id)
        return {
            "id": sim_order_id,
            "entity": "order",
            "amount": amount_minor_units,
            "amount_paid": 0,
            "amount_due": amount_minor_units,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
            "notes": notes,
            "created_at": int(secrets.randbelow(1000000)),
            "simulation_token": simulation_token,
        }

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str, simulation_token: Optional[str] = None) -> bool:
        """
        Verifies Razorpay payment signature server-side.
        In simulation mode, a one-time challenge token is required so a forged signature is not accepted.
        """
        if self.simulation_mode:
            if not simulation_token:
                return False
            expected_token = self._simulation_order_tokens.get(order_id)
            if not expected_token or not secure_compare(expected_token, simulation_token):
                return False
            expected_sig = self.generate_simulation_payment_signature(order_id, payment_id, expected_token)
            return secure_compare(expected_sig, signature)

        secret = settings.RAZORPAY_KEY_SECRET
        payload = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac_sha256(secret, payload)
        return secure_compare(expected_sig, signature)

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verifies Razorpay webhook signature against the RAW request body.
        """
        if not signature_header:
            return False

        if self.simulation_mode:
            digest = hashlib.sha256(raw_body).hexdigest()
            expected_token = self._webhook_tokens.get(digest)
            if expected_token:
                expected_sig = f"sim_webhook_sig_{digest}_{expected_token}"
                return secure_compare(expected_sig, signature_header)
            return False

        secret = settings.RAZORPAY_WEBHOOK_SECRET
        expected_sig = hmac_sha256(secret, raw_body)
        return secure_compare(expected_sig, signature_header)

razorpay_service = RazorpayService()
