from datetime import date, timedelta

from app import models
from app.services import policy_service


def _make_order(status, expected_delivery, cancellable=True):
    return models.Order(order_id="ORD00000", customer_id="CUSTX", status=status,
                         total_amount=100, payment_status="Paid", payment_method="COD",
                         order_date=date.today() - timedelta(days=20),
                         expected_delivery=expected_delivery, cancellable=cancellable)


def _make_product(returnable=True):
    return models.Product(product_id="PRODX", product_name="Test Product", category="Test",
                           price=100, stock_quantity=10, warranty_months=6, returnable=returnable)


def test_return_ineligible_when_not_delivered():
    order = _make_order("Shipped", date.today())
    product = _make_product(True)
    item = models.OrderItem(order_item_id="I1", order_id="ORD00000", product_id="PRODX", quantity=1, unit_price=100)
    result = policy_service.check_return_eligibility(order, product, item)
    assert result["eligible"] is False


def test_return_eligible_within_window():
    order = _make_order("Delivered", date.today() - timedelta(days=2))
    product = _make_product(True)
    item = models.OrderItem(order_item_id="I1", order_id="ORD00000", product_id="PRODX", quantity=1, unit_price=100)
    result = policy_service.check_return_eligibility(order, product, item)
    assert result["eligible"] is True


def test_return_ineligible_after_window():
    order = _make_order("Delivered", date.today() - timedelta(days=30))
    product = _make_product(True)
    item = models.OrderItem(order_item_id="I1", order_id="ORD00000", product_id="PRODX", quantity=1, unit_price=100)
    result = policy_service.check_return_eligibility(order, product, item)
    assert result["eligible"] is False


def test_return_ineligible_when_not_returnable_product():
    order = _make_order("Delivered", date.today() - timedelta(days=1))
    product = _make_product(False)
    item = models.OrderItem(order_item_id="I1", order_id="ORD00000", product_id="PRODX", quantity=1, unit_price=100)
    result = policy_service.check_return_eligibility(order, product, item)
    assert result["eligible"] is False


def test_cancellation_blocked_when_flag_false():
    order = _make_order("Confirmed", date.today() + timedelta(days=3), cancellable=False)
    result = policy_service.check_cancellation_eligibility(order)
    assert result["eligible"] is False


def test_cancellation_blocked_after_delivery():
    order = _make_order("Delivered", date.today(), cancellable=True)
    result = policy_service.check_cancellation_eligibility(order)
    assert result["eligible"] is False


def test_ticket_priority_is_deterministic():
    assert policy_service.determine_ticket_priority("Refund pending") == "urgent"
    assert policy_service.determine_ticket_priority("Product query") == "low"
    assert policy_service.determine_ticket_priority("Something unmapped") == "medium"
