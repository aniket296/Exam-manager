import json
import logging
from typing import Dict, Any
from datetime import timedelta
from sqlalchemy.orm import Session
from backend.models import WebhookEventModel, OrderModel, AttemptModel
from backend.services.razorpay_service import razorpay_service
from backend.services.token_service import generate_exam_credential
from backend.services.sheets_service import sheets_service
from backend.utils.time import utc_now, to_iso

logger = logging.getLogger(__name__)

class WebhookService:
    def process_webhook(self, raw_body: bytes, signature_header: str, db: Session) -> Dict[str, Any]:
        """
        Processes Razorpay webhook payload idempotently.
        Verifies signature against the raw body bytes.
        """
        # 1. Verify signature
        if not razorpay_service.verify_webhook_signature(raw_body, signature_header):
            logger.warning("Rejected webhook due to invalid signature.")
            return {"status": "error", "message": "Invalid webhook signature"}

        # 2. Parse payload safely
        try:
            event_payload = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            logger.error(f"Malformed webhook JSON: {e}")
            return {"status": "error", "message": "Malformed payload"}

        event_id = event_payload.get("event_id") or event_payload.get("id")
        event_type = event_payload.get("event")

        if not event_id or not event_type:
            return {"status": "ignored", "message": "Missing event ID or event type"}

        # 3. Check for duplicate processing
        existing_event = db.query(WebhookEventModel).filter(WebhookEventModel.EventID == event_id).first()
        if existing_event:
            logger.info(f"Webhook event {event_id} already processed. Skipping duplicate.")
            return {"status": "already_processed", "event_id": event_id}

        # 4. Extract entity references
        payload_data = event_payload.get("payload", {})
        payment_entity = payload_data.get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        now = utc_now()
        webhook_log = WebhookEventModel(
            EventID=event_id,
            EventType=event_type,
            OrderID=order_id,
            PaymentID=payment_id,
            ReceivedAt=now,
            ProcessedAt=now,
            ProcessingStatus="PROCESSED"
        )

        try:
            # 5. Handle events
            if event_type == "payment.captured":
                if order_id:
                    order = db.query(OrderModel).filter(OrderModel.OrderID == order_id).first()
                    if order and order.Status == "CREATED":
                        order.Status = "PAID"
                        order.PaymentID = payment_id
                        
                        # Create attempt if not already created
                        existing_attempt = db.query(AttemptModel).filter(AttemptModel.OrderID == order_id).first()
                        if not existing_attempt:
                            import uuid
                            attempt_id = f"att_{uuid.uuid4().hex[:12]}"
                            raw_token, token_hash, token_expiry_iso = generate_exam_credential()
                            new_attempt = AttemptModel(
                                AttemptID=attempt_id,
                                OrderID=order.OrderID,
                                PaymentID=payment_id or f"pay_{uuid.uuid4().hex[:10]}",
                                Name=order.StudentName,
                                StudentIdentifier=order.StudentIdentifier,
                                PhoneOrContact=order.Contact,
                                PaperID=order.PaperID,
                                PaperVersion=order.PaperVersion,
                                AmountMinorUnits=order.AmountMinorUnits,
                                Currency=order.Currency,
                                Status="PAID",
                                AttemptTokenHash=token_hash,
                                TokenCreatedAt=now,
                                TokenExpiresAt=now + timedelta(hours=24),
                                Timestamp=now
                            )
                            db.add(new_attempt)
                            logger.info(f"Created attempt {attempt_id} from webhook payment.captured.")

            elif event_type == "payment.failed":
                if order_id:
                    order = db.query(OrderModel).filter(OrderModel.OrderID == order_id).first()
                    if order and order.Status == "CREATED":
                        order.Status = "FAILED"

            elif event_type in ["refund.created", "refund.processed"]:
                if order_id:
                    order = db.query(OrderModel).filter(OrderModel.OrderID == order_id).first()
                    if order:
                        order.Status = "REFUNDED"
                    attempt = db.query(AttemptModel).filter(AttemptModel.OrderID == order_id).first()
                    if attempt and attempt.Status == "PAID":
                        # If exam hasn't started, revoke access
                        attempt.Status = "EXPIRED"

            db.add(webhook_log)
            db.commit()

            # Sync event log to Google Sheets
            try:
                sheets_service.sync_webhook_event({
                    "EventID": event_id,
                    "EventType": event_type,
                    "OrderID": order_id,
                    "PaymentID": payment_id,
                    "ReceivedAt": to_iso(now),
                    "ProcessedAt": to_iso(now),
                    "ProcessingStatus": "PROCESSED"
                })
            except Exception:
                pass

            return {"status": "success", "event_id": event_id}

        except Exception as e:
            db.rollback()
            webhook_log.ProcessingStatus = "FAILED"
            webhook_log.ErrorMessage = str(e)
            db.add(webhook_log)
            db.commit()
            logger.error(f"Error handling webhook event {event_id}: {e}")
            return {"status": "error", "message": str(e)}

webhook_service = WebhookService()
