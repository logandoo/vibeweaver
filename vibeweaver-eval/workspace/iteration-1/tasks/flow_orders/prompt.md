# Task: build an Order service with account balance

Build a small FastAPI service from scratch in the current directory. A hidden workflow test will start the service and run the full business flow: register → top up balance → place orders (balance deducted atomically) → verify persistence → reject orders exceeding balance.

## API spec (exact contract — hidden tests verify it precisely)

- `POST /api/register` `{"username": str, "password": str}` → `201 {"id": int, "username": str}`; `409` if the username already exists
- `POST /api/login` `{"username": str, "password": str}` → `200 {"token": str}`; `401` if credentials are wrong
- `POST /api/balance/topup` (auth) `{"amount": int > 0}` → `200 {"balance": int}` (adds to current balance)
- `GET /api/balance` (auth) → `200 {"balance": int}`
- `POST /api/orders` (auth) `{"item": str, "price": int > 0}` → `201 {"id": int, "item": str, "price": int}`; `400` if `price` exceeds the current balance; on success the balance MUST be deducted by exactly `price` (atomic — an order cannot be placed twice on the same balance)
- `GET /api/orders` (auth) → `200` list of YOUR OWN orders, each `{"id", "item", "price"}`, oldest first

## Constraints

- Implement in `main.py` using FastAPI + uvicorn. Storage: in-memory or sqlite3 (standard library only, no extra packages).
- The service MUST start with exactly: `python3 -m uvicorn main:app --host 127.0.0.1 --port 8972`
- Tokens: return any non-empty token at login (e.g. random string) and keep them server-side so they validate on later calls.
- Orders and balances must persist across calls within the running service.
- All responses must be JSON.
- Do not modify any files outside the current directory.
