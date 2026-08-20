"""
DISHA Platform - Cryptographic Security & Token Management
Disaster Intelligence and Situational Hazard Awareness Platform

Implements:
- Production-grade Argon2id password hashing & verification
- Cryptographic OTP generation (via secrets module) and HMAC hashing
- Refresh-token SHA-256 hashing for database session storage
- JWT Access and Refresh token lifecycle with claim validation
"""

import hmac
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
    _password_hasher = PasswordHasher(
        time_cost=2,
        memory_cost=65536,  # 64 MiB
        parallelism=1,
        hash_len=32,
    )
    _HAS_ARGON2 = True
except ImportError:
    _password_hasher = None
    _HAS_ARGON2 = False

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hashes a password using Argon2id with a cryptographically secure random salt.
    Falls back to bcrypt if argon2-cffi is not installed.
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")

    if _HAS_ARGON2 and _password_hasher is not None:
        return _password_hasher.hash(password)

    # Fallback to bcrypt
    import bcrypt
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against an Argon2id hash using constant-time comparison.
    Falls back to bcrypt verification if legacy hash is encountered.
    """
    if not plain_password or not hashed_password:
        return False

    # Try Argon2id first if available and hash starts with $argon2
    if _HAS_ARGON2 and _password_hasher is not None and hashed_password.startswith("$argon2"):
        try:
            return _password_hasher.verify(hashed_password, plain_password)
        except Exception:
            return False

    # Secondary check for standard bcrypt
    try:
        import bcrypt
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$") or hashed_password.startswith("$2y$"):
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
    except Exception:
        pass

    return False


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validates that a password satisfies DISHA platform security standards:
    - Minimum length of 8 characters
    - Maximum length of 128 characters
    - At least one uppercase letter
    - At least one numeric digit
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numeric digit."
    return True, None


def generate_secure_otp(length: int = 6) -> str:
    """
    Generates a cryptographically secure numeric OTP using Python's secrets module.
    """
    digits = string.digits
    return "".join(secrets.choice(digits) for _ in range(length))


def hash_otp(otp: str, email: str) -> str:
    """
    Computes an HMAC-SHA256 hash of the OTP bound to the email address
    and application JWT secret. Never stores plaintext OTP in database.
    """
    key = settings.JWT_SECRET.encode("utf-8")
    message = f"{email.lower().strip()}:{otp.strip()}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_otp_hash(plain_otp: str, email: str, stored_hash: str) -> bool:
    """
    Performs constant-time verification of a supplied OTP against the stored HMAC hash.
    """
    if not plain_otp or not email or not stored_hash:
        return False
    computed_hash = hash_otp(plain_otp, email)
    return hmac.compare_digest(computed_hash, stored_hash)


def hash_token(token: str) -> str:
    """
    Computes SHA-256 cryptographic digest of a refresh token.
    Only token hashes are stored in the sessions collection.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    user_id: str,
    session_id: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generates a short-lived JWT Access Token (default: 15 minutes).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "session_id": str(session_id),
        "type": "access",
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    user_id: str,
    session_id: str,
) -> str:
    """
    Generates a long-lived JWT Refresh Token (default: 7 days) with a unique JTI.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "session_id": str(session_id),
        "type": "refresh",
        "jti": secrets.token_hex(16),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_jwt_token(
    token: str,
    expected_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token.
    Raises jwt.PyJWTError subclasses upon failure.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "session_id", "type", "exp"]},
    )
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"Invalid token type: expected '{expected_type}', got '{payload.get('type')}'"
        )
    return payload
