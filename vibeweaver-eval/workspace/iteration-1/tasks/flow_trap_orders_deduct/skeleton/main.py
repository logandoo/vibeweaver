from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI()

users = {}
tokens = {}
balances = {}
orders = {}
next_order = 1


class Reg(BaseModel):
    username: str
    password: str


class Login(BaseModel):
    username: str
    password: str


class Topup(BaseModel):
    amount: int


class Order(BaseModel):
    item: str
    price: int


def auth(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "unauthorized")
    user = tokens.get(authorization[7:])
    if not user:
        raise HTTPException(401, "unauthorized")
    return user


@app.post("/api/register", status_code=201)
def register(body: Reg):
    if body.username in users:
        raise HTTPException(409, "exists")
    users[body.username] = {"id": len(users) + 1, "password": body.password}
    balances[body.username] = 0
    orders[body.username] = []
    return {"id": users[body.username]["id"], "username": body.username}


@app.post("/api/login")
def login(body: Login):
    u = users.get(body.username)
    if not u or u["password"] != body.password:
        raise HTTPException(401, "bad creds")
    token = uuid.uuid4().hex
    tokens[token] = body.username
    return {"token": token}


@app.post("/api/balance/topup")
def topup(body: Topup, authorization: str = Header(None)):
    user = auth(authorization)
    if body.amount <= 0:
        raise HTTPException(400, "invalid amount")
    balances[user] += body.amount
    return {"balance": balances[user]}


@app.get("/api/balance")
def get_balance(authorization: str = Header(None)):
    user = auth(authorization)
    return {"balance": balances.get(user, 0)}


@app.post("/api/orders", status_code=201)
def place_order(body: Order, authorization: str = Header(None)):
    global next_order
    user = auth(authorization)
    if body.price <= 0:
        raise HTTPException(400, "invalid price")
    if body.price > balances.get(user, 0):
        raise HTTPException(400, "insufficient balance")
    o = {"id": next_order, "item": body.item, "price": body.price}
    next_order += 1
    orders[user].append(o)
    return o


@app.get("/api/orders")
def list_orders(authorization: str = Header(None)):
    user = auth(authorization)
    return orders.get(user, [])
