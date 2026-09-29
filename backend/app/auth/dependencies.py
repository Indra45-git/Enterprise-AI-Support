from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.auth.jwt_utils import decode_access_token

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class Identity:
    """The authenticated identity. This is the ONLY source of truth for 'who is asking'.
    It is built from the verified JWT server-side and is never accepted as a parameter
    from the request body or from the LLM/agent."""
    customer_id: str
    role: str


def get_current_identity(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Identity:
    try:
        payload = decode_access_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    customer_id = payload.get("sub")
    role = payload.get("role", "CUSTOMER")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")
    return Identity(customer_id=customer_id, role=role)


def require_role(*allowed_roles: str):
    """Role-based authorization dependency factory.
    Roles: CUSTOMER, SUPPORT_AGENT, ADMIN."""
    def _checker(identity: Identity = Depends(get_current_identity)) -> Identity:
        if identity.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return identity
    return _checker
