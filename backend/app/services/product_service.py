from sqlalchemy.orm import Session

from app import models


def get_product(db: Session, product_id: str) -> models.Product | None:
    return db.query(models.Product).filter(models.Product.product_id == product_id).first()


def product_details(p: models.Product) -> dict:
    return {
        "product_id": p.product_id,
        "product_name": p.product_name,
        "category": p.category,
        "price": p.price,
        "in_stock": (p.stock_quantity or 0) > 0,
        "stock_quantity": p.stock_quantity,
        "warranty_months": p.warranty_months,
        "returnable": p.returnable,
    }
