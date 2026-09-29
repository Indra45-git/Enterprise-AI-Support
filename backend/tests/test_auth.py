def test_login_success(client, two_customers):
    c1, _ = two_customers
    r = client.post("/auth/login", json={"email": c1.email, "password": "demo1234"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client, two_customers):
    c1, _ = two_customers
    r = client.post("/auth/login", json={"email": c1.email, "password": "wrong"})
    assert r.status_code == 401


def test_chat_requires_auth(client):
    r = client.post("/chat", json={"message": "where is my order"})
    assert r.status_code in (401, 403)
