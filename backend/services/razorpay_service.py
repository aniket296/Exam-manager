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
        self.simulation_mode = (
            settings.RAZORPAY_SIMULATION_MODE or 
            settings.RAZORPAY_KEY_ID.startswith("rzp_test_sample")
        )
        if not self.simulation_mode:
            try:
                self.client = razorpay.Client(
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Razorpay Client: {e}. Defaulting to simulation mode.")
                self.simulation_mode = True
                self.client = None
        else:
            self.client = None
            logger.info("Razorpay running in SIMULATION/DEMO mode.")

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
        else:
            # Simulation order
            sim_order_id = f"order_sim_{secrets.token_hex(10)}"
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
                "created_at": int(secrets.randbelow(1000000))
            }

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verifies Razorpay payment signature server-side.
        HMAC-SHA256(order_id + "|" + payment_id, secret) == signature
        """
        secret = settings.RAZORPAY_KEY_SECRET
        payload = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac_sha256(secret, payload)
        
        # Support simulation signature if running in simulation mode
        if self.simulation_mode:
            if signature == f"sim_sig_{order_id}_{payment_id}":
                return True
                
        return secure_compare(expected_sig, signature)

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verifies Razorpay webhook signature against the RAW request body.
        HMAC-SHA256(raw_body, webhook_secret) == signature_header
        """
        if not signature_header:
            return False
            
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        expected_sig = hmac_sha256(secret, raw_body)
        
        if self.simulation_mode and signature_header.startswith("sim_webhook_sig"):
            return True
            
        return secure_compare(expected_sig, signature_header)

razorpay_service = RazorpayService()

