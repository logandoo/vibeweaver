import httpx

BASE = "http://127.0.0.1:8973"


def test_todo_auth_workflow():
    c = httpx.Client(base_url=BASE, timeout=5)
    # register two users
    r = c.post("/api/register", json={"username": "alice", "password": "pw1"})
    assert r.status_code == 201, r.text
    r = c.post("/api/register", json={"username": "alice", "password": "pw1"})
    assert r.status_code == 409, r.text
    r = c.post("/api/register", json={"username": "bob", "password": "pw2"})
    assert r.status_code == 201, r.text
    # login: wrong creds rejected
    r = c.post("/api/login", json={"username": "alice", "password": "wrong"})
    assert r.status_code == 401, r.text
    r = c.post("/api/login", json={"username": "alice", "password": "pw1"})
    assert r.status_code == 200, r.text
    token_a = r.json()["token"]
    assert token_a, "login must return a non-empty token"
    r = c.post("/api/login", json={"username": "bob", "password": "pw2"})
    assert r.status_code == 200, r.text
    token_b = r.json()["token"]
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}
    # create todos
    r = c.post("/api/todos", headers=ha, json={"title": "alpha"})
    assert r.status_code == 201, r.text
    todo_id = r.json()["id"]
    r = c.post("/api/todos", headers=ha, json={"title": "beta"})
    assert r.status_code == 201, r.text
    # list own todos
    r = c.get("/api/todos", headers=ha)
    assert r.status_code == 200, r.text
    titles = [t["title"] for t in r.json()]
    assert "alpha" in titles and "beta" in titles, r.text
    # bob cannot see alice's todos
    r = c.get("/api/todos", headers=hb)
    assert r.status_code == 200 and all(t["owner"] != "alice" for t in r.json()), r.text
    # update own todo
    r = c.patch(f"/api/todos/{todo_id}", headers=ha, json={"done": True})
    assert r.status_code == 200, r.text
    assert r.json()["done"] is True, r.text
    # cross-user update forbidden
    r = c.patch(f"/api/todos/{todo_id}", headers=hb, json={"done": True})
    assert r.status_code == 403, r.text
    # delete own todo
    r = c.delete(f"/api/todos/{todo_id}", headers=ha)
    assert r.status_code == 200, r.text
    r = c.get("/api/todos", headers=ha)
    assert all(t["id"] != todo_id for t in r.json()), r.text
    # unauthenticated access rejected
    r = c.get("/api/todos")
    assert r.status_code == 401, r.text
