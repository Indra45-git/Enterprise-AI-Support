import uuid
from datetime import date

from sqlalchemy.orm import Session

from app import models
from app.services.policy_service import determine_ticket_priority


def get_ticket(db: Session, ticket_id: str) -> models.SupportTicket | None:
    return db.query(models.SupportTicket).filter(models.SupportTicket.ticket_id == ticket_id).first()


def list_my_tickets(db: Session, customer_id: str) -> list[dict]:
    tickets = db.query(models.SupportTicket).filter(
        models.SupportTicket.customer_id == customer_id
    ).order_by(models.SupportTicket.created_at.desc()).all()
    return [ticket_status(t) for t in tickets]


def ticket_status(t: models.SupportTicket) -> dict:
    return {
        "ticket_id": t.ticket_id,
        "issue_type": t.issue_type,
        "priority": t.priority,
        "status": t.status,
        "assigned_to": t.assigned_to,
        "order_id": t.order_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "escalation_reason": t.escalation_reason,
    }


def create_ticket(db: Session, customer_id: str, issue_type: str, description: str,
                   order_id: str | None, idempotency_key: str | None = None) -> dict:
    # Idempotency: if a ticket already exists for this key, return it instead of duplicating.
    if idempotency_key:
        existing = db.query(models.SupportTicket).filter(
            models.SupportTicket.ticket_id == f"IDEM-{idempotency_key}"
        ).first()
        if existing:
            return {"created": False, "ticket": ticket_status(existing)}

    ticket_id = f"IDEM-{idempotency_key}" if idempotency_key else f"TKT-{uuid.uuid4().hex[:8].upper()}"
    priority = determine_ticket_priority(issue_type)  # deterministic, not LLM-decided
    t = models.SupportTicket(
        ticket_id=ticket_id, customer_id=customer_id, order_id=order_id,
        issue_type=issue_type, description=description, priority=priority,
        status="open", assigned_to="AI_AGENT", created_at=date.today(),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"created": True, "ticket": ticket_status(t)}


def escalate_ticket(db: Session, ticket: models.SupportTicket, reason: str) -> dict:
    ticket.status = "escalated"
    ticket.assigned_to = "SUPPORT_AGENT_QUEUE"
    ticket.escalation_reason = reason
    db.commit()
    db.refresh(ticket)
    return ticket_status(ticket)
