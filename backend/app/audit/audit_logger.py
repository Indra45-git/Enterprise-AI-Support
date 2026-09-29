import json
import uuid
from datetime import datetime, timezone

from app.config import AUDIT_LOG_PATH


def log_event(*, user_id: str, session_id: str, action: str, tool: str | None,
              resource_id: str | None, authorization_result: str,
              execution_result: str, trace_id: str | None = None) -> dict:
    """Every sensitive action must be auditable. Deliberately does NOT store
    raw PII (name/email/phone/address) - only IDs and outcomes."""
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "session_id": session_id,
        "action": action,
        "tool": tool,
        "resource_id": resource_id,
        "authorization_result": authorization_result,
        "execution_result": execution_result,
        "trace_id": trace_id or str(uuid.uuid4()),
    }
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        # Deliberately ignore filesystem write errors in serverless/read-only environments
        pass
    return event
