import secrets
from datetime import timedelta
from typing import Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import get_db, AdminSessionModel
from backend.utils.time import utc_now
from backend.utils.hashing import verify_password, sha256_hash

security_bearer = HTTPBearer(auto_error=False)

def authenticate_admin_password(password: str) -> bool:
    """Verifies plain text password against settings.ADMIN_PASSWORD_HASH."""
    if not settings.ADMIN_PASSWORD_HASH:
        return False
    return verify_password(password, settings.ADMIN_PASSWORD_HASH)

def create_admin_session(db: Session) -> Tuple[str, str]:
    """Generates a secure admin session token and saves its hash/expiry."""
    token = secrets.token_urlsafe(48)
    token_hash = sha256_hash(token)
    expires_at = utc_now() + timedelta(minutes=settings.ADMIN_SESSION_EXPIRE_MINUTES)
    
    # Save session
    session_obj = AdminSessionModel(
        SessionToken=token_hash,
        ExpiresAt=expires_at
    )
    db.add(session_obj)
    db.commit()
    return token, expires_at.isoformat()

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> AdminSessionModel:
    """Dependency verifying admin bearer token."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    token = credentials.credentials
    token_hash = sha256_hash(token)
    
    session_obj = db.query(AdminSessionModel).filter(AdminSessionModel.SessionToken == token_hash).first()
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired admin session.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    now = utc_now()
    if session_obj.ExpiresAt.tzinfo is None:
        expires_at = session_obj.ExpiresAt.replace(tzinfo=utc_now().tzinfo)
    else:
        expires_at = session_obj.ExpiresAt
        
    if now > expires_at:
        db.delete(session_obj)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return session_obj
