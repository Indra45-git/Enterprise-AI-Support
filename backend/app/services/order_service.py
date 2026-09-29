from sqlalchemy.orm import Session

from app import models


def list_my_orders(db: Session, customer_id: str) -> list[dict]:
    orders = db.query(models.Order).filter(models.Order.customer_id == customer_id).all()
    result = []
    for o in orders:
        row = _minimal_order(o)
        # Include a compact product summary so the customer can see what they ordered
        row["items"] = [
            {
                "product_name": item.product.product_name if item.product else item.product_id,
                "quantity": item.quantity,
            }
            for item in o.items
        ]
        result.append(row)
    return result


def get_order(db: Session, order_id: str) -> models.Order | None:
    return db.query(models.Order).filter(models.Order.order_id == order_id).first()


def get_order_details(db: Session, order: models.Order) -> dict:
    items = []
    for item in order.items:
        items.append({
            "product_id": item.product_id,
            "product_name": item.product.product_name if item.product else item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
        })
    data = _minimal_order(order)
    data["items"] = items
    return data


def _minimal_order(o: models.Order) -> dict:
    """Data minimization: only what's needed to answer order questions -
    no customer PII (name/email/phone/address) is included here."""
    return {
        "order_id": o.order_id,
        "status": o.status,
        "total_amount": o.total_amount,
        "payment_status": o.payment_status,
        "payment_method": o.payment_method,
        "order_date": o.order_date.isoformat() if o.order_date else None,
        "expected_delivery": o.expected_delivery.isoformat() if o.expected_delivery else None,
        "cancellable": o.cancellable,
        "tracking_number": o.tracking_number,
    }
