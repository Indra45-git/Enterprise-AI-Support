from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.auth.dependencies import get_current_identity, Identity
from app.tools.tool_gateway import call_tool, ToolError
from app.schemas import CreateTicketArgs, EscalateTicketArgs

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("")
def list_my_tickets(identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    tickets = db.query(models.SupportTicket).filter(
        models.SupportTicket.customer_id == identity.customer_id
    ).order_by(models.SupportTicket.created_at.desc()).all()
    return [{
        "ticket_id": t.ticket_id,
        "issue_type": t.issue_type,
        "description": t.description,
        "priority": t.priority,
        "status": t.status,
        "assigned_to": t.assigned_to,
        "order_id": t.order_id,
        "created_at": str(t.created_at) if t.created_at else None,
        "escalation_reason": t.escalation_reason,
    } for t in tickets]


@router.get("/{ticket_id}")
def ticket_status(ticket_id: str, identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    try:
        res = call_tool("get_ticket_status", {"ticket_id": ticket_id}, identity, db)
    except ToolError as e:
        raise HTTPException(status_code=403 if e.code == "forbidden" else 404, detail=e.message)
    return res["data"]


@router.post("")
def create_ticket(payload: CreateTicketArgs, identity: Identity = Depends(get_current_identity),
                   db: Session = Depends(get_db), idempotency_key: str | None = Header(default=None)):
    try:
        res = call_tool("create_support_ticket", payload.model_dump(), identity, db,
                         idempotency_key=idempotency_key)
    except ToolError as e:
        raise HTTPException(status_code=403 if e.code == "forbidden" else 400, detail=e.message)
    return res["data"]


@router.post("/{ticket_id}/escalate")
def escalate(ticket_id: str, payload: dict, identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    args = EscalateTicketArgs(ticket_id=ticket_id, reason=payload.get("reason", "")).model_dump()
    try:
        res = call_tool("escalate_ticket", args, identity, db)
    except ToolError as e:
        raise HTTPException(status_code=403 if e.code == "forbidden" else 400, detail=e.message)
    return res["data"]
