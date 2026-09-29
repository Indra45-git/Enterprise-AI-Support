"""
Deterministic business rules.

Design principle: "Backend determines truth, LLM explains truth."
None of these decisions are ever delegated to the LLM. The agent may only
*present* what these functions return - it cannot override, negotiate, or
invent a different outcome.
"""
from datetime import date, timedelta

from app import models
from app.config import RETURN_WINDOW_DAYS, ESCALATION_WAIT_DAYS

NON_CANCELLABLE_STATUSES = {"Delivered", "Cancelled", "Out for Delivery"}

# Deterministic priority table for new tickets (issue_type -> priority)
ISSUE_PRIORITY_MAP = {
    "Refund pending": "urgent",
    "Wrong item": "urgent",
    "Missing item": "high",
    "Delivery complaint": "high",
    "Damaged item": "high",
    "Payment issue": "urgent",
    "Product query": "low",
    "Cancellation request": "medium",
    "Other": "low",
}


def check_return_eligibility(order: models.Order, product: models.Product, item: models.OrderItem | None) -> dict:
    if item is None:
        return {"eligible": False, "reason": "This product was not part of that order."}
    if not product.returnable:
        return {"eligible": False, "reason": f"{product.product_name} is marked as non-returnable."}
    if order.status not in ("Delivered",):
        return {"eligible": False, "reason": f"Order is '{order.status}'; returns open only after delivery."}
    if not order.expected_delivery:
        return {"eligible": False, "reason": "No delivery date on record for this order."}
    deadline = order.expected_delivery + timedelta(days=RETURN_WINDOW_DAYS)
    today = date.today()
    if today > deadline:
        return {"eligible": False, "reason": f"Return window ({RETURN_WINDOW_DAYS} days after delivery) ended on {deadline.isoformat()}."}
    return {"eligible": True, "reason": f"Eligible for return until {deadline.isoformat()}."}


def check_cancellation_eligibility(order: models.Order) -> dict:
    if not order.cancellable:
        return {"eligible": False, "reason": "This order is flagged as non-cancellable."}
    if order.status in NON_CANCELLABLE_STATUSES:
        return {"eligible": False, "reason": f"Order status '{order.status}' can no longer be cancelled."}
    return {"eligible": True, "reason": "Order can be cancelled."}


def check_warranty_validity(product: models.Product, order: models.Order) -> dict:
    if not order.order_date:
        return {"valid": False, "reason": "No order date on record."}
    if not product.warranty_months:
        return {"valid": False, "reason": f"{product.product_name} carries no warranty."}
    expiry_month = order.order_date.month - 1 + product.warranty_months
    expiry_year = order.order_date.year + expiry_month // 12
    expiry_month = expiry_month % 12 + 1
    try:
        expiry = date(expiry_year, expiry_month, min(order.order_date.day, 28))
    except ValueError:
        expiry = date(expiry_year, expiry_month, 1)
    valid = date.today() <= expiry
    return {"valid": valid, "warranty_expires": expiry.isoformat(),
            "reason": "Warranty active." if valid else "Warranty period has ended."}


def determine_ticket_priority(issue_type: str) -> str:
    return ISSUE_PRIORITY_MAP.get(issue_type, "medium")


def should_auto_escalate(ticket: models.SupportTicket) -> dict:
    """Policy-based escalation: urgent tickets left waiting for the customer/agent
    beyond ESCALATION_WAIT_DAYS are flagged for escalation automatically."""
    if ticket.status in ("resolved", "closed"):
        return {"escalate": False, "reason": "Ticket already closed."}
    if not ticket.created_at:
        return {"escalate": False, "reason": "No creation date on record."}
    age_days = (date.today() - ticket.created_at).days
    if ticket.priority == "urgent" and age_days >= ESCALATION_WAIT_DAYS:
        return {"escalate": True, "reason": f"Urgent ticket open for {age_days} days (threshold {ESCALATION_WAIT_DAYS})."}
    return {"escalate": False, "reason": "Does not yet meet escalation threshold."}


# Human-in-the-loop risk classification, per the spec's risk table.
RISK_AUTOMATIC = "automatic"
RISK_CONFIRM = "customer_confirmation"
RISK_HUMAN = "human_approval"

TOOL_RISK_LEVEL = {
    "get_my_orders": RISK_AUTOMATIC,
    "get_order_status": RISK_AUTOMATIC,
    "get_order_details": RISK_AUTOMATIC,
    "get_product_details": RISK_AUTOMATIC,
    "check_return_eligibility": RISK_AUTOMATIC,
    "get_ticket_status": RISK_AUTOMATIC,
    "get_my_tickets": RISK_AUTOMATIC,
    "create_support_ticket": RISK_AUTOMATIC,
    "escalate_ticket": RISK_AUTOMATIC,          # policy-based, deterministic rule above
    "cancel_order": RISK_CONFIRM,               # not exposed as an LLM tool by default; needs explicit confirm
    "request_refund": RISK_HUMAN,               # always routed to a human agent
}
