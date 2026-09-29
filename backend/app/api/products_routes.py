from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.auth.dependencies import get_current_identity, Identity
from app.tools.tool_gateway import call_tool, ToolError

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(query: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Product)
    if query:
        term = f"%{query.strip()}%"
        q = q.filter(models.Product.product_name.ilike(term) | models.Product.product_id.ilike(term))
    if category:
        q = q.filter(models.Product.category.ilike(f"%{category.strip()}%"))
    products = q.limit(50).all()
    return [{
        "product_id": p.product_id,
        "product_name": p.product_name,
        "category": p.category,
        "price": p.price,
        "stock_quantity": p.stock_quantity,
        "warranty_months": p.warranty_months,
        "returnable": p.returnable,
    } for p in products]


@router.get("/{product_id}")
def product_details(product_id: str, identity: Identity = Depends(get_current_identity), db: Session = Depends(get_db)):
    try:
        res = call_tool("get_product_details", {"product_id": product_id}, identity, db)
    except ToolError as e:
        raise HTTPException(status_code=404, detail=e.message)
    return res["data"]
