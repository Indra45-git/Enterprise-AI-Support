"""
Tool Gateway.

Every tool call from the agent passes through here, in this order:
  1. Schema validation (Pydantic)          -> reject malformed args
  2. Rate limiting                         -> reject abusive callers
  3. Authentication is already done        -> Identity comes from the verified JWT
  4. Authorization / ownership check       -> e.g. does this order belong to this customer?
  5. Business rules (policy_service)       -> deterministic, not LLM-decided
  6. Idempotency (for write tools)         -> re-running create_support_ticket is safe
  7. Execution against the service layer   -> parameterized ORM calls only, never raw SQL
  8. Audit logging                         -> every call, success or failure
  9. Data minimization                     -> only fields relevant to the task go back

The agent (agent/agent.py) NEVER touches the database or SQLAlchemy directly - it only
calls call_tool(name, args, identity).
"""
import time
from collections import defaultdict, deque

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import schemas
from app.auth.dependencies import Identity
from app.audit.audit_logger import log_event
from app.observability.metrics import increment, timer
from app.services import order_service, product_service, ticket_service, policy_service
from app.config import RATE_LIMIT_PER_MINUTE

# --- naive in-memory rate limiter (swap for Redis token-bucket in production) ---
_call_log: dict[str, deque] = defaultdict(deque)


def _rate_limited(customer_id: str) -> bool:
    now = time.time()
    window = _call_log[customer_id]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        return True
    window.append(now)
    return False


# --- naive in-memory idempotency store (swap for Redis in production) ---
_idempotency_store: set[str] = set()


class ToolError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def call_tool(tool_name: str, args: dict, identity: Identity, db: Session,
              session_id: str = "n/a", idempotency_key: str | None = None) -> dict:
    trace_id = f"{session_id}-{tool_name}-{int(time.time()*1000)}"

    if _rate_limited(identity.customer_id):
        log_event(user_id=identity.customer_id, session_id=session_id, action="tool_call",
                   tool=tool_name, resource_id=None, authorization_result="rate_limited",
                   execution_result="blocked", trace_id=trace_id)
        raise ToolError("rate_limited", "Too many requests. Please slow down and try again shortly.")

    increment(f"tool.{tool_name}.calls")
    with timer(f"tool.{tool_name}.latency"):
        try:
            result = _dispatch(tool_name, args, identity, db, idempotency_key)
            log_event(user_id=identity.customer_id, session_id=session_id, action="tool_call",
                       tool=tool_name, resource_id=str(args.get("order_id") or args.get("ticket_id") or args.get("product_id") or ""),
                       authorization_result="allowed", execution_result="success", trace_id=trace_id)
            return {"ok": True, "data": result}
        except ValidationError as e:
            log_event(user_id=identity.customer_id, session_id=session_id, action="tool_call",
                       tool=tool_name, resource_id=None, authorization_result="n/a",
                       execution_result="invalid_arguments", trace_id=trace_id)
            raise ToolError("invalid_arguments", f"Invalid arguments for {tool_name}: {e.errors()[0]['msg']}")
        except ToolError as e:
            log_event(user_id=identity.customer_id, session_id=session_id, action="tool_call",
                       tool=tool_name, resource_id=None, authorization_result="denied",
                       execution_result=e.code, trace_id=trace_id)
            raise
        except Exception as e:  # pragma: no cover - safety net
            log_event(user_id=identity.customer_id, session_id=session_id, action="tool_call",
                       tool=tool_name, resource_id=None, authorization_result="n/a",
                       execution_result=f"error:{type(e).__name__}", trace_id=trace_id)
            raise ToolError("internal_error", "Something went wrong handling that request.")


def _dispatch(tool_name: str, args: dict, identity: Identity, db: Session, idempotency_key: str | None) -> dict:
    if tool_name == "get_my_orders":
        return {"orders": order_service.list_my_orders(db, identity.customer_id)}

    if tool_name == "get_order_status":
        a = schemas.OrderIdArg(**args)
        order = _owned_order(db, a.order_id, identity)
        return {"order_id": order.order_id, "status": order.status,
                "expected_delivery": order.expected_delivery.isoformat() if order.expected_delivery else None}

    if tool_name == "get_order_details":
        a = schemas.OrderIdArg(**args)
        order = _owned_order(db, a.order_id, identity)
        return order_service.get_order_details(db, order)

    if tool_name == "get_product_details":
        a = schemas.ProductIdArg(**args)
        product = product_service.get_product(db, a.product_id)
        if not product:
            raise ToolError("not_found", f"No product {a.product_id}.")
        return product_service.product_details(product)

    if tool_name == "check_return_eligibility":
        a = schemas.ReturnEligibilityArgs(**args)
        order = _owned_order(db, a.order_id, identity)
        product = product_service.get_product(db, a.product_id)
        if not product:
            raise ToolError("not_found", f"No product {a.product_id}.")
        item = next((i for i in order.items if i.product_id == a.product_id), None)
        return policy_service.check_return_eligibility(order, product, item)

    if tool_name == "get_my_tickets":
        return {"tickets": ticket_service.list_my_tickets(db, identity.customer_id)}

    if tool_name == "get_ticket_status":
        a = schemas.TicketIdArg(**args)
        ticket = _owned_ticket(db, a.ticket_id, identity)
        return ticket_service.ticket_status(ticket)

    if tool_name == "create_support_ticket":
        a = schemas.CreateTicketArgs(**args)
        if a.order_id:
            _owned_order(db, a.order_id, identity)  # 404/403 if not theirs
        return ticket_service.create_ticket(
            db, identity.customer_id, a.issue_type, a.description, a.order_id,
            idempotency_key=idempotency_key,
        )

    if tool_name == "escalate_ticket":
        a = schemas.EscalateTicketArgs(**args)
        ticket = _owned_ticket(db, a.ticket_id, identity)
        return ticket_service.escalate_ticket(db, ticket, a.reason)

    raise ToolError("unknown_tool", f"Tool '{tool_name}' is not an approved capability.")


def _owned_order(db: Session, order_id: str, identity: Identity):
    order = order_service.get_order(db, order_id)
    if not order:
        raise ToolError("not_found", f"No order {order_id}.")
    if identity.role != "ADMIN" and order.customer_id != identity.customer_id:
        # Zero-trust ownership check - prevents IDOR; only the owner can access this order.
        raise ToolError("forbidden", "That order does not belong to your account.")
    return order


def _owned_ticket(db: Session, ticket_id: str, identity: Identity):
    ticket = ticket_service.get_ticket(db, ticket_id)
    if not ticket:
        raise ToolError("not_found", f"No ticket {ticket_id}.")
    if identity.role != "ADMIN" and ticket.customer_id != identity.customer_id:
        # Zero-trust ownership check - prevents IDOR; only the owner can access this ticket.
        raise ToolError("forbidden", "That ticket does not belong to your account.")
    return ticket

