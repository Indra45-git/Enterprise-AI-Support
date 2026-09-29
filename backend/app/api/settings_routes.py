from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create_settings(db: Session, bot_id: str = "default") -> models.ChatbotSetting:
    setting = db.query(models.ChatbotSetting).filter(models.ChatbotSetting.bot_id == bot_id).first()
    if not setting:
        setting = models.ChatbotSetting(
            bot_id=bot_id,
            bot_name="Apex AI Support",
            welcome_message="Hello! 👋 I'm your AI customer support assistant. How can I help you today?",
            primary_color="#6366f1",
            secondary_color="#4f46e5",
            avatar_icon="🤖",
            placeholder_text="Ask about orders, returns, tracking, policies…",
            suggested_questions="Where is my order ORD00012?|What is your return policy?|Can I return an item?|Open a support ticket",
            system_instructions="You are an enterprise AI support assistant. Answer accurately based on verified company policy and database results.",
            is_public=True,
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


@router.get("")
@router.get("/{bot_id}")
def get_settings(bot_id: str = "default", db: Session = Depends(get_db)):
    setting = _get_or_create_settings(db, bot_id)
    return {
        "bot_id": setting.bot_id,
        "bot_name": setting.bot_name,
        "welcome_message": setting.welcome_message,
        "primary_color": setting.primary_color,
        "secondary_color": setting.secondary_color,
        "avatar_icon": setting.avatar_icon,
        "placeholder_text": setting.placeholder_text,
        "suggested_questions": [q.strip() for q in setting.suggested_questions.split("|") if q.strip()],
        "suggested_questions_raw": setting.suggested_questions,
        "system_instructions": setting.system_instructions,
        "is_public": setting.is_public,
    }


@router.post("/reset")
@router.post("/{bot_id}/reset")
def reset_settings(bot_id: str = "default", db: Session = Depends(get_db)):
    setting = _get_or_create_settings(db, bot_id)
    setting.bot_name = "Apex AI Support"
    setting.welcome_message = "Hello! 👋 I'm your AI customer support assistant. How can I help you today?"
    setting.primary_color = "#6366f1"
    setting.secondary_color = "#4f46e5"
    setting.avatar_icon = "🤖"
    setting.placeholder_text = "Ask about orders, returns, tracking, policies…"
    setting.suggested_questions = "Where is my order ORD00012?|What is your return policy?|Can I return an item?|Open a support ticket"
    setting.system_instructions = "You are an enterprise AI support assistant. Answer accurately based on verified company policy and database results."
    setting.is_public = True
    db.commit()
    return {"status": "reset", "bot_id": bot_id}


@router.post("")
@router.put("")
@router.post("/{bot_id}")
@router.put("/{bot_id}")
def update_settings(payload: schemas.ChatbotSettingsUpdate, bot_id: str = "default", db: Session = Depends(get_db)):
    setting = _get_or_create_settings(db, bot_id)
    if payload.bot_name is not None:
        setting.bot_name = payload.bot_name
    if payload.welcome_message is not None:
        setting.welcome_message = payload.welcome_message
    if payload.primary_color is not None:
        setting.primary_color = payload.primary_color
    if payload.secondary_color is not None:
        setting.secondary_color = payload.secondary_color
    if payload.avatar_icon is not None:
        setting.avatar_icon = payload.avatar_icon
    if payload.placeholder_text is not None:
        setting.placeholder_text = payload.placeholder_text
    if payload.suggested_questions is not None:
        setting.suggested_questions = payload.suggested_questions
    if payload.system_instructions is not None:
        setting.system_instructions = payload.system_instructions
    if payload.is_public is not None:
        setting.is_public = payload.is_public

    db.commit()
    db.refresh(setting)
    return {
        "status": "success",
        "settings": {
            "bot_id": setting.bot_id,
            "bot_name": setting.bot_name,
            "welcome_message": setting.welcome_message,
            "primary_color": setting.primary_color,
            "secondary_color": setting.secondary_color,
            "avatar_icon": setting.avatar_icon,
            "placeholder_text": setting.placeholder_text,
            "suggested_questions": [q.strip() for q in setting.suggested_questions.split("|") if q.strip()],
            "suggested_questions_raw": setting.suggested_questions,
            "system_instructions": setting.system_instructions,
            "is_public": setting.is_public,
        }
    }

