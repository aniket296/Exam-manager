import secrets
from datetime import timedelta
from typing import Tuple
from backend.config import settings
from backend.utils.time import utc_now
from backend.utils.hashing import sha256_hash

def generate_exam_credential() -> Tuple[str, str, str]:
    """
    Generates an unguessable cryptographically secure attempt token.
    Returns:
        raw_token: To be delivered to the client securely once.
        token_hash: SHA-256 hash to be stored in the datastore.
        token_expires_at_iso: Expiration timestamp in ISO format.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = sha256_hash(raw_token)
    expires_at = utc_now() + timedelta(hours=settings.ATTEMPT_TOKEN_EXPIRE_HOURS)
    return raw_token, token_hash, expires_at.isoformat()

