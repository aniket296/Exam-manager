import os
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import get_db, PaperModel, OrderModel, AttemptModel
from backend.schemas import (
    PaymentCreateOrderRequest, PaymentCreateOrderResponse,
    PaymentVerifyRequest, PaymentVerifyResponse,
    PinVerifyRequest, PinVerifyResponse
)
from backend.security.rate_limit import check_rate_limit
from backend.services.razorpay_service import razorpay_service
from backend.services.token_service import generate_exam_credential
from backend.services.sheets_service import sheets_service
from backend.utils.time import utc_now, to_iso

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/create-order", response_model=PaymentCreateOrderResponse)
def create_payment_order(
    payload: PaymentCreateOrderRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Creates an order for assessment purchase.
    Enforces authoritative backend pricing - client prices are completely ignored.
    """
    check_rate_limit(request, max_requests=15, window_seconds=60)

    # 1. Authoritative Paper Validation
    paper = db.query(PaperModel).filter(
        PaperModel.PaperID == payload.PaperID,
        PaperModel.Status == "PUBLISHED"
    ).first()

    if not paper:
        raise HTTPException(status_code=404, detail="Assessment paper not available for purchase.")

    now = utc_now()

    # 2. Check for reusable recent unpaid order to avoid duplicate spam
    recent_order = db.query(OrderModel).filter(
        OrderModel.PaperID == paper.PaperID,
        OrderModel.StudentName == payload.StudentName.strip(),
        OrderModel.Status == "CREATED",
        OrderModel.ExpiresAt > now
    ).first()

    reusable_simulation_token = razorpay_service._simulation_order_tokens.get(recent_order.OrderID) if recent_order else None
    if recent_order and (not razorpay_service.simulation_mode or reusable_simulation_token):
        return PaymentCreateOrderResponse(
            OrderID=recent_order.OrderID,
            PaperID=paper.PaperID,
            Title=paper.Title,
            AmountMinorUnits=recent_order.AmountMinorUnits,
            Currency=recent_order.Currency,
            KeyID=settings.RAZORPAY_KEY_ID,
            SimulationMode=razorpay_service.simulation_mode,
            SimulationToken=reusable_simulation_token
        )

    # 3. Create Razorpay order with authoritative price
    receipt = f"rec_{uuid.uuid4().hex[:10]}"
    notes = {
        "PaperID": paper.PaperID,
        "StudentName": payload.StudentName.strip(),
        "StudentIdentifier": payload.StudentIdentifier or ""
    }

    try:
        rzp_order = razorpay_service.create_order(
            amount_minor_units=paper.PriceMinorUnits,
            currency=paper.Currency,
            receipt=receipt,
            notes=notes
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment gateway communication failed. Please try again."
        )

    order_id = rzp_order["id"]
    simulation_token = rzp_order.get("simulation_token")

    # 4. Save Order in Transactional DB
    new_order = OrderModel(
        OrderID=order_id,
        PaperID=paper.PaperID,
        PaperVersion=paper.Version,
        AmountMinorUnits=paper.PriceMinorUnits,
        Currency=paper.Currency,
        Status="CREATED",
        StudentName=payload.StudentName.strip(),
        StudentIdentifier=payload.StudentIdentifier or "",
        Contact=payload.Contact or "",
        CreatedAt=now,
        ExpiresAt=now + timedelta(minutes=30)
    )
    db.add(new_order)
    db.commit()

    return PaymentCreateOrderResponse(
        OrderID=order_id,
        PaperID=paper.PaperID,
        Title=paper.Title,
        AmountMinorUnits=paper.PriceMinorUnits,
        Currency=paper.Currency,
        KeyID=settings.RAZORPAY_KEY_ID,
        SimulationMode=razorpay_service.simulation_mode,
        SimulationToken=simulation_token
    )

@router.post("/verify", response_model=PaymentVerifyResponse)
def verify_payment(
    payload: PaymentVerifyRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authoritative payment verification.
    Verifies Razorpay HMAC signature, prevents replay attacks, and generates secure exam credentials.
    """
    check_rate_limit(request, max_requests=20, window_seconds=60)

    # 1. Locate Order
    order = db.query(OrderModel).filter(OrderModel.OrderID == payload.OrderID).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    # 2. Check if already verified/consumed
    existing_attempt = db.query(AttemptModel).filter(AttemptModel.OrderID == payload.OrderID).first()
    if existing_attempt:
        # If attempt already exists, return friendly message without creating duplicate attempt
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment has already been processed for this test."
        )

    # 3. Check if PaymentID was already consumed
    consumed_payment = db.query(AttemptModel).filter(AttemptModel.PaymentID == payload.PaymentID).first()
    if consumed_payment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This payment reference has already been used."
        )

    # 4. Authoritative Signature Verification
    is_valid = razorpay_service.verify_payment_signature(
        order_id=payload.OrderID,
        payment_id=payload.PaymentID,
        signature=payload.Signature,
        simulation_token=payload.SimulationToken
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification signature failed."
        )

    now = utc_now()

    # 5. Mark Order Paid
    order.Status = "PAID"
    order.PaymentID = payload.PaymentID

    # 6. Generate Secure Exam Access Credential
    attempt_id = f"att_{uuid.uuid4().hex[:12]}"
    raw_token, token_hash, token_expires_iso = generate_exam_credential()

    new_attempt = AttemptModel(
        AttemptID=attempt_id,
        OrderID=order.OrderID,
        PaymentID=payload.PaymentID,
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
        TokenExpiresAt=now + timedelta(hours=settings.ATTEMPT_TOKEN_EXPIRE_HOURS),
        Timestamp=now
    )
    db.add(new_attempt)
    db.commit()

    # 7. Sync Attempt to Google Sheets
    try:
        sheets_service.sync_attempt({
            "AttemptID": new_attempt.AttemptID,
            "OrderID": new_attempt.OrderID,
            "PaymentID": new_attempt.PaymentID,
            "Name": new_attempt.Name,
            "StudentIdentifier": new_attempt.StudentIdentifier,
            "PhoneOrContact": new_attempt.PhoneOrContact,
            "PaperID": new_attempt.PaperID,
            "PaperVersion": new_attempt.PaperVersion,
            "AmountMinorUnits": new_attempt.AmountMinorUnits,
            "Currency": new_attempt.Currency,
            "Status": new_attempt.Status,
            "AttemptTokenHash": new_attempt.AttemptTokenHash,
            "TokenCreatedAt": to_iso(new_attempt.TokenCreatedAt),
            "TokenExpiresAt": to_iso(new_attempt.TokenExpiresAt),
            "StrikeCount": 0,
            "Timestamp": to_iso(new_attempt.Timestamp)
        })
    except Exception:
        pass

    return PaymentVerifyResponse(
        Success=True,
        AttemptToken=raw_token,
        AttemptID=attempt_id,
        Message="Payment verified successfully. You may now begin your test!"
    )

@router.post("/verify-pin", response_model=PinVerifyResponse)
def verify_access_pin(
    payload: PinVerifyRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Access PIN bypass endpoint.
    Checks if the provided PIN matches os.getenv("ACCESS_PIN", "02112005").
    If valid, creates order and paid attempt, syncs to Google Sheets, and returns attempt session token.
    If invalid, returns HTTP 400.
    """
    check_rate_limit(request, max_requests=20, window_seconds=60)

    # 1. Verify Access PIN
    expected_pin = os.getenv("ACCESS_PIN", "02112005")
    if payload.pin.strip() != expected_pin.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Access PIN. Please check and try again."
        )

    # 2. Verify Assessment Paper
    paper = db.query(PaperModel).filter(PaperModel.PaperID == payload.paper_id.strip()).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Assessment paper not found.")

    student_name = payload.name.strip()
    phone_contact = payload.phone.strip() if payload.phone else ""
    now = utc_now()

    # 3. Create Order Record (Marked as PAID via PIN)
    order_id = f"ord_pin_{uuid.uuid4().hex[:10]}"
    payment_id = f"pay_pin_{uuid.uuid4().hex[:10]}"

    new_order = OrderModel(
        OrderID=order_id,
        PaperID=paper.PaperID,
        PaperVersion=paper.Version,
        AmountMinorUnits=paper.PriceMinorUnits,
        Currency=paper.Currency,
        Status="PAID",
        StudentName=student_name,
        StudentIdentifier=phone_contact,
        Contact=phone_contact,
        PaymentID=payment_id,
        CreatedAt=now,
        ExpiresAt=now + timedelta(hours=24)
    )
    db.add(new_order)

    # 4. Generate Authoritative Exam Credentials
    attempt_id = f"att_{uuid.uuid4().hex[:12]}"
    raw_token, token_hash, token_expires_iso = generate_exam_credential()

    new_attempt = AttemptModel(
        AttemptID=attempt_id,
        OrderID=order_id,
        PaymentID=payment_id,
        Name=student_name,
        StudentIdentifier=phone_contact,
        PhoneOrContact=phone_contact,
        PaperID=paper.PaperID,
        PaperVersion=paper.Version,
        AmountMinorUnits=paper.PriceMinorUnits,
        Currency=paper.Currency,
        Status="PAID",
        AttemptTokenHash=token_hash,
        TokenCreatedAt=now,
        TokenExpiresAt=now + timedelta(hours=settings.ATTEMPT_TOKEN_EXPIRE_HOURS),
        Timestamp=now
    )
    db.add(new_attempt)
    db.commit()

    # 5. Sync to Google Sheets
    try:
        sheets_service.sync_attempt({
            "AttemptID": new_attempt.AttemptID,
            "OrderID": new_attempt.OrderID,
            "PaymentID": new_attempt.PaymentID,
            "Name": new_attempt.Name,
            "StudentIdentifier": new_attempt.StudentIdentifier,
            "PhoneOrContact": new_attempt.PhoneOrContact,
            "PaperID": new_attempt.PaperID,
            "PaperVersion": new_attempt.PaperVersion,
            "AmountMinorUnits": new_attempt.AmountMinorUnits,
            "Currency": new_attempt.Currency,
            "Status": "PAID",
            "AttemptTokenHash": new_attempt.AttemptTokenHash,
            "TokenCreatedAt": to_iso(new_attempt.TokenCreatedAt),
            "TokenExpiresAt": to_iso(new_attempt.TokenExpiresAt),
            "StrikeCount": 0,
            "Timestamp": to_iso(new_attempt.Timestamp)
        })
    except Exception:
        pass

    return PinVerifyResponse(
        Success=True,
        AttemptToken=raw_token,
        AttemptID=attempt_id,
        Message="Access PIN verified successfully. Starting assessment."
    )

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Razorpay Webhook receiver.
    Requires and verifies signature over the raw HTTP request body.
    """
    raw_body = await request.body()
    from backend.services.webhook_service import webhook_service
    result = webhook_service.process_webhook(raw_body, x_razorpay_signature or "", db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
