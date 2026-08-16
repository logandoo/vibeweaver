import httpx

BASE = "http://127.0.0.1:8972"


def test_order_balance_workflow():
    c = httpx.Client(base_url=BASE, timeout=5)
    # register + login
    r = c.post("/api/register", json={"username": "buyer", "password": "pw"})
    assert r.status_code == 201, r.text
    r = c.post("/api/register", json={"username": "buyer", "password": "pw"})
    assert r.status_code == 409, r.text
    r = c.post("/api/login", json={"username": "buyer", "password": "pw"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    h = {"Authorization": f"Bearer {token}"}
    # top up
    r = c.post("/api/balance/topup", headers=h, json={"amount": 100})
    assert r.status_code == 200, r.text
    assert r.json()["balance"] == 100, r.text
    r = c.get("/api/balance", headers=h)
    assert r.json()["balance"] == 100, r.text
    # order over balance rejected
    r = c.post("/api/orders", headers=h, json={"item": "widget", "price": 150})
    assert r.status_code == 400, r.text
    r = c.get("/api/balance", headers=h)
    assert r.json()["balance"] == 100, "rejected order must not deduct balance"
    # valid order deducts exactly price
    r = c.post("/api/orders", headers=h, json={"item": "widget", "price": 40})
    assert r.status_code == 201, r.text
    r = c.get("/api/balance", headers=h)
    assert r.json()["balance"] == 60, r.text
    # order persisted
    r = c.get("/api/orders", headers=h)
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1, r.text
    assert r.json()[0]["item"] == "widget" and r.json()[0]["price"] == 40, r.text
    # second order drains balance
    r = c.post("/api/orders", headers=h, json={"item": "gadget", "price": 60})
    assert r.status_code == 201, r.text
    r = c.get("/api/balance", headers=h)
    assert r.json()["balance"] == 0, r.text
    # insufficient balance now
    r = c.post("/api/orders", headers=h, json={"item": "more", "price": 1})
    assert r.status_code == 400, r.text
    # unauthenticated access rejected
    r = c.get("/api/orders")
    assert r.status_code == 401, r.text
