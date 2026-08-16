# Task: fix the Order service

The current directory contains an implementation of an Order service with account balance. The service looks complete and basic usage appears to work, but hidden workflow tests will verify the FULL business flow: register → login → top up balance → place orders → check balance → list orders, including correct atomic balance accounting (each successful order must deduct exactly its price from the balance, once).

Investigate the implementation, find anything that breaks the flow across calls, fix it, and verify the complete flow yourself.

## API spec (hidden tests verify it precisely)

- `POST /api/register` `{"username", "password"}` → `201 {"id", "username"}`; `409` if exists
- `POST /api/login` → `200 {"token"}`; `401` on wrong credentials
- `POST /api/balance/topup` (auth) `{"amount": int > 0}` → `200 {"balance"}` (adds to balance)
- `GET /api/balance` (auth) → `200 {"balance"}`
- `POST /api/orders` (auth) `{"item", "price": int > 0}` → `201 {"id", "item", "price"}`; `400` if price exceeds balance; on success the balance MUST be reduced by exactly `price`, and this must happen every time (orders cannot consume the same balance twice)
- `GET /api/orders` (auth) → `200` your orders, oldest first

## Constraints

- The service MUST start with exactly: `python3 -m uvicorn main:app --host 127.0.0.1 --port 8974`
- Balance accounting must be correct across the whole sequence of calls (topup → order → balance check → more orders).
- All responses JSON. Do not modify files outside the current directory.
