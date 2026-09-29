import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.auth.dependencies import get_current_identity, Identity
from app.agent.agent import handle_message

router = APIRouter(prefix="/chat", tags=["chat"])


def _save_history(db: Session, session_id: str, customer_id: str | None, bot_id: str,
                  user_msg: str, bot_reply: str, blocked: bool):
    try:
        sess = db.query(models.ChatSession).filter(models.ChatSession.session_id == session_id).first()
        if not sess:
            sess = models.ChatSession(
                session_id=session_id,
                customer_id=customer_id,
                bot_id=bot_id,
                created_at=date.today(),
                last_active=date.today(),
            )
            db.add(sess)
        else:
            sess.last_active = date.today()
            if customer_id and not sess.customer_id:
                sess.customer_id = customer_id

        db.add(models.ChatMessage(session_id=session_id, sender="user", content=user_msg, created_at=date.today()))
        db.add(models.ChatMessage(session_id=session_id, sender="guardrail" if blocked else "bot",
                                  content=bot_reply, created_at=date.today()))
        db.commit()
    except Exception:
        pass


@router.post("")
def chat(payload: schemas.ChatRequest, identity: Identity = Depends(get_current_identity),
          db: Session = Depends(get_db)):
    session_id = payload.session_id or str(uuid.uuid4())
    # Look up customer name for personalized greetings
    customer = db.query(models.Customer).filter(
        models.Customer.customer_id == identity.customer_id
    ).first()
    customer_name = customer.name if customer else None
    result = handle_message(payload.message, identity, db, session_id, customer_name=customer_name)
    _save_history(db, session_id, identity.customer_id, payload.bot_id or "default",
                  payload.message, result.reply, result.blocked)
    return {
        "session_id": session_id,
        "reply": result.reply,
        "tool_calls": result.tool_calls,
        "blocked": result.blocked,
    }


@router.post("/public")
def public_chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Chat endpoint for embeddable widget visitors (no enterprise JWT required)."""
    session_id = payload.session_id or str(uuid.uuid4())
    bot_id = payload.bot_id or "default"
    visitor_identity = Identity(customer_id="VISITOR", role="VISITOR")
    result = handle_message(payload.message, visitor_identity, db, session_id, customer_name="Guest")
    _save_history(db, session_id, None, bot_id, payload.message, result.reply, result.blocked)
    return {
        "session_id": session_id,
        "reply": result.reply,
        "tool_calls": result.tool_calls,
        "blocked": result.blocked,
    }


from fastapi import Header, HTTPException

@router.get("/history/{session_id}")
def get_chat_history(session_id: str, db: Session = Depends(get_db),
                     authorization: str | None = Header(default=None)):
    """Returns conversation history for a given session with tenant isolation."""
    sess = db.query(models.ChatSession).filter(models.ChatSession.session_id == session_id).first()
    if sess and sess.customer_id:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authentication required to view customer chat history")
        from app.auth.jwt_utils import decode_access_token
        try:
            payload = decode_access_token(authorization.split(" ", 1)[1])
            if payload.get("role") != "ADMIN" and payload.get("sub") != sess.customer_id:
                raise HTTPException(status_code=403, detail="Forbidden: You cannot access another customer's chat session")
        except Exception:
            raise HTTPException(status_code=403, detail="Invalid token for this session")

    msgs = db.query(models.ChatMessage).filter(
        models.ChatMessage.session_id == session_id
    ).order_by(models.ChatMessage.id.asc()).all()
    return [{"id": m.id, "sender": m.sender, "content": m.content, "created_at": str(m.created_at)} for m in msgs]

