from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES


def create_access_token(customer_id: str, role: str = "CUSTOMER") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": customer_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises JWTError on invalid/expired token."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
