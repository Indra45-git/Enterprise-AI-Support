from fastapi import APIRouter, Depends, HTTPException
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.auth.jwt_utils import create_access_token
from app.auth.dependencies import get_current_identity

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.email == payload.email).first()
    if not customer or not bcrypt.verify(payload.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(customer_id=customer.customer_id, role="CUSTOMER")
    return {"access_token": token, "token_type": "bearer", "customer_id": customer.customer_id,
            "customer_name": customer.name, "customer_tier": customer.customer_tier, "email": customer.email}


@router.get("/demo-customers")
def get_demo_customers(db: Session = Depends(get_db)):
    """Curated list of demo customers for instant 1-click testing."""
    customers = db.query(models.Customer).limit(8).all()
    out = []
    for c in customers:
        order_count = len(c.orders) if c.orders else 0
        ticket_count = len(c.tickets) if c.tickets else 0
        out.append({
            "customer_id": c.customer_id,
            "name": c.name,
            "email": c.email,
            "customer_tier": c.customer_tier or "Standard",
            "city": c.city or "",
            "order_count": order_count,
            "ticket_count": ticket_count,
        })
    return out


@router.get("/me")
def get_me(identity=Depends(get_current_identity), db: Session = Depends(get_db)):
    customer = db.query(models.Customer).filter(models.Customer.customer_id == identity.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "city": customer.city,
        "state": customer.state,
        "customer_tier": customer.customer_tier,
        "order_count": len(customer.orders) if customer.orders else 0,
        "ticket_count": len(customer.tickets) if customer.tickets else 0,
    }

