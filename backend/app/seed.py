"""
Loads customers.csv / products.csv / orders.csv / order_items.csv / support_tickets.csv
(the provided AI_Agent_100_Users_DB_Dataset) into the configured database.

Run with:  python -m app.seed
"""
import csv
from datetime import datetime
from pathlib import Path

from passlib.hash import bcrypt

from app.database import Base, engine, SessionLocal
from app import models
from app.config import DEMO_PASSWORD, BASE_DIR

SEED_DIR = Path(BASE_DIR) / "data" / "seed"


def _date(s):
    if not s:
        return None
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def _bool(s):
    return str(s).strip().lower() == "true"


def _float(s):
    return float(s) if s not in (None, "") else None


def _int(s):
    return int(s) if s not in (None, "") else None


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    demo_hash = bcrypt.hash(DEMO_PASSWORD)

    try:
        with open(SEED_DIR / "customers.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                db.add(models.Customer(
                    customer_id=row["customer_id"], name=row["name"], email=row["email"],
                    phone=row["phone"], city=row["city"], state=row["state"],
                    pincode=row["pincode"], customer_tier=row["customer_tier"],
                    created_at=_date(row["created_at"]), password_hash=demo_hash,
                ))
        db.commit()

        with open(SEED_DIR / "products.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                db.add(models.Product(
                    product_id=row["product_id"], product_name=row["product_name"],
                    category=row["category"], price=_float(row["price"]),
                    stock_quantity=_int(row["stock_quantity"]),
                    warranty_months=_int(row["warranty_months"]),
                    returnable=_bool(row["returnable"]),
                ))
        db.commit()

        with open(SEED_DIR / "orders.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                db.add(models.Order(
                    order_id=row["order_id"], customer_id=row["customer_id"],
                    status=row["status"], total_amount=_float(row["total_amount"]),
                    payment_status=row["payment_status"], payment_method=row["payment_method"],
                    order_date=_date(row["order_date"]),
                    expected_delivery=_date(row["expected_delivery"]),
                    cancellable=_bool(row["cancellable"]),
                    tracking_number=row["tracking_number"] or None,
                ))
        db.commit()

        with open(SEED_DIR / "order_items.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                db.add(models.OrderItem(
                    order_item_id=row["order_item_id"], order_id=row["order_id"],
                    product_id=row["product_id"], quantity=_int(row["quantity"]),
                    unit_price=_float(row["unit_price"]),
                ))
        db.commit()

        with open(SEED_DIR / "support_tickets.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                db.add(models.SupportTicket(
                    ticket_id=row["ticket_id"], customer_id=row["customer_id"],
                    order_id=row["order_id"] or None, issue_type=row["issue_type"],
                    description=row["description"], priority=row["priority"],
                    status=row["status"], assigned_to=row["assigned_to"],
                    created_at=_date(row["created_at"]),
                ))
        db.commit()

        # Seed default chatbot settings
        db.add(models.ChatbotSetting(
            bot_id="default",
            bot_name="Apex AI Support",
            welcome_message="Hello! 👋 I'm your AI customer support assistant. How can I assist you with orders, returns, or questions today?",
            primary_color="#6366f1",
            secondary_color="#4f46e5",
            avatar_icon="🤖",
            placeholder_text="Ask about orders, returns, tracking, policies…",
            suggested_questions="Where is my order ORD00012?|What is your return policy?|Can I return an item?|Open a support ticket",
            system_instructions="You are an enterprise AI support assistant. Answer accurately based on verified company policy and database results.",
            is_public=True
        ))
        db.commit()

        print(f"Seeded: {db.query(models.Customer).count()} customers, "
              f"{db.query(models.Product).count()} products, "
              f"{db.query(models.Order).count()} orders, "
              f"{db.query(models.OrderItem).count()} order_items, "
              f"{db.query(models.SupportTicket).count()} tickets, "
              f"and default chatbot settings.")
        print(f"Demo login password for every seeded customer: {DEMO_PASSWORD!r} (change in production)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
