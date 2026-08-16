# Task: build a Todo API with token authentication

Build a small FastAPI service from scratch in the current directory. A hidden workflow test will start the service and run the full business flow: register → login → create todos → list → update → delete, including cross-user and unauthenticated access checks.

## API spec (exact contract — hidden tests verify it precisely)

- `POST /api/register` `{"username": str, "password": str}` → `201 {"id": int, "username": str}`; `409` if the username already exists
- `POST /api/login` `{"username": str, "password": str}` → `200 {"token": str}`; `401` if credentials are wrong
- `POST /api/todos` (header `Authorization: Bearer <token>`) `{"title": str}` → `201 {"id": int, "title": str, "owner": str, "done": false}`; `401` without a valid token
- `GET /api/todos` (auth) → `200` list of YOUR OWN todos only, each `{"id", "title", "owner", "done"}`
- `PATCH /api/todos/{id}` (auth) `{"done": bool}` → `200` updated todo; `403` if the todo belongs to another user; `404` if it does not exist
- `DELETE /api/todos/{id}` (auth) → `200`; `403` if it belongs to another user

## Constraints

- Implement in `main.py` using FastAPI + uvicorn. Storage: in-memory or sqlite3 (standard library only, no extra packages).
- The service MUST start with exactly: `python3 -m uvicorn main:app --host 127.0.0.1 --port 8971`
- Tokens: return any non-empty token at login (e.g. random string) and keep them server-side so they validate on later calls.
- All responses must be JSON.
- Do not modify any files outside the current directory.
