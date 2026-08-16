from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI()

users = {}
tokens = {}
todos = []
next_id = 1


class Reg(BaseModel):
    username: str
    password: str


class Login(BaseModel):
    username: str
    password: str


class TodoIn(BaseModel):
    title: str


class TodoPatch(BaseModel):
    done: bool


def auth(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "unauthorized")
    token = authorization[7:]
    user = tokens.get(token)
    if not user:
        raise HTTPException(401, "unauthorized")
    return user


@app.post("/api/register", status_code=201)
def register(body: Reg):
    if body.username in users:
        raise HTTPException(409, "exists")
    uid = len(users) + 1
    users[body.username] = {"id": uid, "password": body.password}
    return {"id": uid, "username": body.username}


@app.post("/api/login")
def login(body: Login):
    u = users.get(body.username)
    if not u or u["password"] != body.password:
        raise HTTPException(401, "bad creds")
    token = uuid.uuid4().hex
    tokens[token] = body.username
    return {"token": token}


@app.post("/api/todos", status_code=201)
def create_todo(body: TodoIn, authorization: str = Header(None)):
    global next_id
    user = auth(authorization)
    t = {"id": next_id, "title": body.title, "owner": user, "done": False}
    next_id += 1
    todos.append(t)
    return t


@app.get("/api/todos")
def list_todos(authorization: str = Header(None)):
    auth(authorization)
    return todos


@app.patch("/api/todos/{tid}")
def update_todo(tid: int, body: TodoPatch, authorization: str = Header(None)):
    auth(authorization)
    for t in todos:
        if t["id"] == tid:
            t["done"] = body.done
            return t
    raise HTTPException(404, "missing")


@app.delete("/api/todos/{tid}")
def delete_todo(tid: int, authorization: str = Header(None)):
    auth(authorization)
    for i, t in enumerate(todos):
        if t["id"] == tid:
            del todos[i]
            return {"ok": True}
    raise HTTPException(404, "missing")
