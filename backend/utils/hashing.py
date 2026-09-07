import hashlib
import hmac
import secrets

def sha256_hash(data: str) -> str:
    """Computes SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def hmac_sha256(key: str, data: bytes) -> str:
    """Computes HMAC-SHA256 hex digest of binary data with a key."""
    return hmac.new(key.encode("utf-8"), data, hashlib.sha256).hexdigest()

def secure_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 600,000 iterations."""
    salt = secrets.token_hex(16)
    iterations = 600_000
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${key.hex()}"

def verify_password(plain_password: str, hashed: str) -> bool:
    """Verifies a plain password against a pbkdf2_sha256 hash."""
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        )
        return hmac.compare_digest(key.hex(), expected_hex)
    except Exception:
        return False

