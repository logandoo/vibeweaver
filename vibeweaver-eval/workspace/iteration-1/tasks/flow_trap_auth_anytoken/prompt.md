# Task: fix the Todo API service

The current directory contains an implementation of a Todo API with token authentication. The service looks complete and basic usage appears to work, but hidden workflow tests will verify the FULL business flow across multiple users and calls: register → login → create todos → list → update → delete, including cross-user isolation (users must only see and modify their own todos) and unauthenticated access.

Investigate the implementation, find anything that breaks the flow across users or across calls, fix it, and verify the complete flow yourself.

## API spec (hidden tests verify it precisely)

- `POST /api/register` `{"username", "password"}` → `201 {"id", "username"}`; `409` if the username already exists
- `POST /api/login` `{"username", "password"}` → `200 {"token"}`; `401` on wrong credentials
- `POST /api/todos` (auth) `{"title"}` → `201 {"id", "title", "owner", "done": false}`; `401` without a valid token
- `GET /api/todos` (auth) → `200` YOUR OWN todos only
- `PATCH /api/todos/{id}` (auth) `{"done": bool}` → `200`; `403` if not the owner; `404` if missing
- `DELETE /api/todos/{id}` (auth) → `200`; `403` if not the owner

## Constraints

- The service MUST start with exactly: `python3 -m uvicorn main:app --host 127.0.0.1 --port 8975`
- Tokens must be validated server-side; each user's requests must only ever see and affect their own data.
- All responses JSON. Do not modify files outside the current directory.
