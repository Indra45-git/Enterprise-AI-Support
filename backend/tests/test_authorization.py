from app import models


def test_customer_cannot_access_other_customers_order(client, db_session, token_for, two_customers):
    c1, c2 = two_customers
    other_order = db_session.query(models.Order).filter(models.Order.customer_id == c2.customer_id).first()
    assert other_order is not None

    token = token_for(c1.customer_id)
    r = client.get(f"/orders/{other_order.order_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_customer_can_access_own_order(client, db_session, token_for, two_customers):
    c1, _ = two_customers
    own_order = db_session.query(models.Order).filter(models.Order.customer_id == c1.customer_id).first()
    assert own_order is not None

    token = token_for(c1.customer_id)
    r = client.get(f"/orders/{own_order.order_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["order_id"] == own_order.order_id


def test_invalid_order_id_format_rejected(client, token_for, two_customers):
    c1, _ = two_customers
    token = token_for(c1.customer_id)
    r = client.get("/orders/DROP TABLE orders", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (400, 404, 422)


def test_visitor_cannot_access_customer_order(db_session, two_customers):
    from app.tools.tool_gateway import call_tool, ToolError
    from app.auth.dependencies import Identity
    c1, _ = two_customers
    own_order = db_session.query(models.Order).filter(models.Order.customer_id == c1.customer_id).first()
    visitor = Identity(customer_id="VISITOR", role="VISITOR")
    try:
        call_tool("get_order_details", {"order_id": own_order.order_id}, visitor, db_session)
        assert False, "Visitor should not be able to access customer orders"
    except ToolError as e:
        assert e.code == "forbidden"


def test_customer_cannot_access_other_customers_ticket(client, db_session, token_for, two_customers):
    c1, c2 = two_customers
    other_ticket = db_session.query(models.SupportTicket).filter(models.SupportTicket.customer_id == c2.customer_id).first()
    if other_ticket:
        token = token_for(c1.customer_id)
        r = client.get(f"/tickets/{other_ticket.ticket_id}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


def test_chat_history_tenant_isolation(client, db_session, token_for, two_customers):
    from datetime import date
    c1, c2 = two_customers
    # Create private chat session for c1
    sess = models.ChatSession(session_id="private-sess-c1", customer_id=c1.customer_id,
                              created_at=date.today(), last_active=date.today())
    db_session.add(sess)
    db_session.commit()

    # Unauthenticated attempt should be blocked
    r1 = client.get("/chat/history/private-sess-c1")
    assert r1.status_code in (401, 403)

    # c2 attempt to read c1 session should be blocked with 403
    token_c2 = token_for(c2.customer_id)
    r2 = client.get("/chat/history/private-sess-c1", headers={"Authorization": f"Bearer {token_c2}"})
    assert r2.status_code == 403

    # c1 attempt should succeed with 200
    token_c1 = token_for(c1.customer_id)
    r3 = client.get("/chat/history/private-sess-c1", headers={"Authorization": f"Bearer {token_c1}"})
    assert r3.status_code == 200

