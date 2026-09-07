from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.models import get_db, AttemptModel
from backend.utils.time import utc_now
from backend.utils.hashing import sha256_hash

attempt_bearer = HTTPBearer(auto_error=False)

def get_current_attempt(
    credentials: HTTPAuthorizationCredentials = Depends(attempt_bearer),
    db: Session = Depends(get_db)
) -> AttemptModel:
    """
    Authoritative attempt authentication dependency.
    Validates Bearer token hash against database and checks token expiration.
    Returns AttemptModel if valid.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your test session could not be verified. Please make sure your test link is active.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    raw_token = credentials.credentials.strip()
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your test session could not be verified.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token_hash = sha256_hash(raw_token)
    attempt = db.query(AttemptModel).filter(AttemptModel.AttemptTokenHash == token_hash).first()
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your test session was not found. Please contact your teacher or parent.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    now = utc_now()
    token_expiry = attempt.TokenExpiresAt
    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=now.tzinfo)

    if now > token_expiry:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Your test pass has expired. Please contact support."
        )

    return attempt

