def test_chatbot_settings_get(client):
    res = client.get("/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["bot_name"] == "Apex AI Support"
    assert "suggested_questions" in data
    assert data["primary_color"] == "#6366f1"


def test_chatbot_settings_update(client):
    res = client.post("/settings", json={
        "bot_name": "Custom Support Bot",
        "primary_color": "#10b981",
        "welcome_message": "Hello from custom bot!",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["settings"]["bot_name"] == "Custom Support Bot"
    assert data["settings"]["primary_color"] == "#10b981"

    # Verify get returns updated
    get_res = client.get("/settings")
    assert get_res.json()["bot_name"] == "Custom Support Bot"


def test_products_list(client):
    res = client.get("/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) > 0
    assert "product_id" in products[0]
    assert "price" in products[0]


def test_demo_customers(client):
    res = client.get("/auth/demo-customers")
    assert res.status_code == 200
    customers = res.json()
    assert len(customers) > 0
    assert "email" in customers[0]
    assert "customer_tier" in customers[0]


def test_customer_list_tickets(client, two_customers, token_for):
    c1, _ = two_customers
    token = token_for(c1.customer_id)
    res = client.get("/tickets", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    tickets = res.json()
    assert isinstance(tickets, list)


def test_public_widget_chat(client):
    res = client.post("/chat/public", json={"message": "What is your return policy?"})
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert data["blocked"] is False


def test_chatbot_settings_reset(client):
    # Modify settings first
    client.post("/settings", json={"bot_name": "Temporary Bot"})
    # Call reset
    res = client.post("/settings/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "reset"
    # Verify settings are back to default
    get_res = client.get("/settings")
    assert get_res.json()["bot_name"] == "Apex AI Support"


def test_product_details_has_name_and_stock(client, two_customers, token_for):
    c1, _ = two_customers
    token = token_for(c1.customer_id)
    res = client.get("/products/PROD0001", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == "PROD0001"
    assert "product_name" in data
    assert "stock_quantity" in data


def test_create_ticket_empty_order_id_and_lowercase():
    from app.schemas import CreateTicketArgs
    t1 = CreateTicketArgs(issue_type="Wrong item", description="Wrong color received", order_id="")
    assert t1.order_id is None
    t2 = CreateTicketArgs(issue_type="Wrong item", description="Wrong color received", order_id="ord00012")
    assert t2.order_id == "ORD00012"


def test_agent_get_my_tickets_intent(client, two_customers, token_for):
    c1, _ = two_customers
    token = token_for(c1.customer_id)
    res = client.post("/chat", json={"message": "List all my support tickets"},
                       headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "get_my_tickets" in data.get("tool_calls", [])

