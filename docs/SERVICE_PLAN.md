# Fidelity Trader Service — Implementation Plan

> **Prerequisite:** This plan is Phase 2 of the project roadmap. Phase 1 (completing Trader+ API coverage in the SDK) takes priority. The service layer is only as useful as the SDK it wraps — see [`BACKLOG.md`](BACKLOG.md) for remaining SDK work. Service implementation should begin once the core trading workflow is complete (single-leg options, order modification, conditional orders, L2 streaming).

> **Goal:** Wrap the fidelity-trader-sdk Python library in a self-hosted REST/WebSocket service that any language or tool can consume, with centralized session management, streaming fan-out, and Docker deployment.

**Architecture:** FastAPI service that imports the SDK as a dependency, manages Fidelity sessions in a background process, exposes all 23+ API modules as REST endpoints, and fans out MDDS WebSocket quotes via Server-Sent Events or WebSocket. Deployed as a Docker container targeting Linux.

**Tech Stack:** FastAPI, Uvicorn, SQLite (session/credential storage), Redis (optional — streaming pub/sub), Docker, fidelity-trader-sdk (this library)

---

## Design Decisions

### Service Boundary

The service is a **thin wrapper** around the SDK. It does not reimplement any Fidelity protocol logic — it delegates entirely to the SDK's existing modules. The service adds:

- HTTP API surface (REST + WebSocket/SSE)
- Session lifecycle management (login, keep-alive, re-auth)
- Credential storage (encrypted at rest)
- Streaming connection management and fan-out
- API key authentication for service consumers
- Docker packaging for self-hosted deployment

### What Stays in the SDK

The SDK remains the sole implementation of Fidelity protocol logic. The service never bypasses the SDK to call Fidelity directly. This means:

- All 23 API modules remain in `fidelity-trader-sdk`
- MDDS WebSocket parsing stays in the SDK
- Pydantic models stay in the SDK
- Auth handshake logic stays in the SDK
- The service imports and composes `FidelityClient` like any other consumer

### Session Management

Fidelity sessions are cookie-based and expire after ~30 minutes of inactivity. The service must:

1. Maintain a `FidelityClient` instance per Fidelity account
2. Track session state (authenticated, expired, 2FA pending)
3. Auto-extend sessions via the `/extendsession` endpoint (backlog item 1.7)
4. Re-authenticate transparently when sessions expire
5. Persist session metadata across service restarts (SQLite)

### Credential Storage

Two modes:

1. **Stored credentials** — Fidelity username/password/TOTP secret stored encrypted in SQLite using Fernet symmetric encryption. The encryption key is provided via environment variable (`FTSERVICE_ENCRYPTION_KEY`). Best for unattended bots.

2. **Pass-through** — Consumer provides credentials on each login call. Service holds the session but not the credentials. Better for interactive use or when the consumer manages secrets externally (Vault, AWS SM, etc.).

### Consumer Authentication

The service itself needs auth to prevent unauthorized access:

- **API key** — Generated on first setup or via CLI command. Passed as `Authorization: Bearer <key>` header.
- **Local-only mode** — Binds to `127.0.0.1` only, no auth required. For single-machine use.
- **No multi-tenancy** — This is a self-hosted personal service, not a SaaS platform. One service instance = one user. Multiple Fidelity accounts are supported, but they all belong to the same service operator.

### Streaming Architecture

```
Fidelity MDDS WebSocket (1 connection per service)
        │
        ▼
┌─────────────────────┐
│  MDDSManager        │  Background asyncio task
│  - Maintains WS     │  - Reconnects on disconnect
│  - Parses quotes    │  - Manages subscriptions
│  - Fans out to      │
│    connected clients │
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼
  SSE      WebSocket      (consumer connections)
/stream   /ws/quotes
```

- One MDDS connection to Fidelity, regardless of how many consumers are connected
- Consumers subscribe to symbols via REST; the manager aggregates and deduplicates
- Quotes pushed to consumers via SSE (simpler, works through proxies) or WebSocket (lower latency)
- If no consumers are subscribed, the MDDS connection is idle (no unnecessary traffic)

---

## API Design

### Base URL

```
http://localhost:8787/api/v1
```

Port 8787 chosen to avoid conflicts with common dev ports (3000, 5000, 8000, 8080).

### Endpoints

#### Auth & Session

```
POST   /auth/login              Login with Fidelity credentials
POST   /auth/login/totp         Submit TOTP code (if 2FA required)
POST   /auth/logout             Logout and clear session
GET    /auth/status             Session status (authenticated, expired, etc.)
POST   /auth/credentials        Store encrypted credentials for auto-login
DELETE /auth/credentials        Remove stored credentials
```

#### Accounts & Portfolio

```
GET    /accounts                         Discover all accounts
GET    /accounts/{acct}/positions        Positions for an account
GET    /accounts/{acct}/balances         Balances for an account
GET    /accounts/{acct}/transactions     Transaction history
GET    /accounts/{acct}/options-summary  Option positions summary
GET    /accounts/{acct}/closed-positions Closed positions (gain/loss)
GET    /accounts/{acct}/loaned-securities Fully paid lending rates
GET    /accounts/{acct}/tax-lots/{symbol} Tax lot details
```

#### Orders

```
POST   /orders/equity/preview            Preview equity order
POST   /orders/equity/place              Place equity order
POST   /orders/options/preview           Preview multi-leg option order
POST   /orders/options/place             Place multi-leg option order
GET    /orders/status                    All open/recent orders
POST   /orders/{order_id}/cancel         Cancel an order
```

#### Market Data

```
GET    /market-data/chain/{symbol}       Option chain
GET    /market-data/montage/{symbol}     Depth of market (per-exchange)
GET    /market-data/chart/{symbol}       Historical chart data
GET    /market-data/markets/{symbol}     Available markets/exchanges
```

#### Research

```
GET    /research/earnings?symbols=AAPL,MSFT    Earnings data
GET    /research/dividends?symbols=AAPL,KO     Dividend data
GET    /research/search?q=AAPL                 Symbol autosuggest
POST   /research/analytics                     Option position analytics
```

#### Watchlists & Alerts

```
GET    /watchlists                       All watchlists
GET    /alerts/subscribe                 Subscribe to alerts
```

#### Preferences

```
GET    /preferences/{path}               Get preferences
PUT    /preferences/{path}               Save preferences
DELETE /preferences/{path}               Delete preferences
```

#### Streaming

```
GET    /streaming/quotes                 SSE stream of real-time quotes
WS     /ws/quotes                        WebSocket stream of real-time quotes
POST   /streaming/subscribe              Subscribe to symbols
POST   /streaming/unsubscribe            Unsubscribe from symbols
GET    /streaming/subscriptions          Current subscriptions
```

#### Service Management

```
GET    /health                           Health check
GET    /service/info                     Service version, SDK version, uptime
POST   /service/api-key                  Generate new API key
```

### Response Format

All responses follow a consistent envelope:

```json
{
  "ok": true,
  "data": { ... },
  "error": null
}
```

Error responses:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "SESSION_EXPIRED",
    "message": "Fidelity session has expired. Re-authenticate.",
    "details": { ... }
  }
}
```

### Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `AUTH_REQUIRED` | 401 | Not logged in to Fidelity |
| `SESSION_EXPIRED` | 401 | Fidelity session expired |
| `TOTP_REQUIRED` | 403 | 2FA code needed |
| `API_KEY_INVALID` | 403 | Invalid or missing service API key |
| `FIDELITY_ERROR` | 502 | Fidelity API returned an error |
| `ORDER_REJECTED` | 422 | Order preview/place was rejected |
| `INVALID_REQUEST` | 400 | Bad request parameters |
| `STREAMING_UNAVAILABLE` | 503 | MDDS connection not established |

---

## File Structure

```
fidelity-trader-sdk/
├── src/fidelity_trader/          # Existing SDK (unchanged)
│
├── service/                      # New: service layer
│   ├── __init__.py
│   ├── __main__.py               # python -m service / uvicorn entrypoint
│   ├── app.py                    # FastAPI app factory
│   ├── config.py                 # Settings (pydantic-settings)
│   ├── dependencies.py           # FastAPI dependency injection (session, auth)
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── api_key.py            # API key generation, validation
│   │   └── middleware.py         # API key auth middleware
│   │
│   ├── session/
│   │   ├── __init__.py
│   │   ├── manager.py            # FidelityClient lifecycle manager
│   │   ├── store.py              # SQLite session/credential persistence
│   │   └── keepalive.py          # Background session keep-alive task
│   │
│   ├── streaming/
│   │   ├── __init__.py
│   │   ├── manager.py            # MDDS connection manager + fan-out
│   │   ├── sse.py                # SSE endpoint
│   │   └── ws.py                 # WebSocket endpoint
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py               # /auth/* routes
│   │   ├── accounts.py           # /accounts/* routes
│   │   ├── orders.py             # /orders/* routes
│   │   ├── market_data.py        # /market-data/* routes
│   │   ├── research.py           # /research/* routes
│   │   ├── watchlists.py         # /watchlists/* routes
│   │   ├── preferences.py        # /preferences/* routes
│   │   ├── streaming.py          # /streaming/* routes
│   │   └── service.py            # /health, /service/* routes
│   │
│   └── models/
│       ├── __init__.py
│       ├── requests.py           # Request body schemas
│       ├── responses.py          # Response envelope + error schemas
│       └── config.py             # Config/credential storage schemas
│
├── docker/
│   ├── Dockerfile                # Multi-stage build
│   ├── docker-compose.yml        # Service + optional Redis
│   └── .env.example              # Environment variable template
│
├── tests/
│   ├── test_service_*.py         # Service-layer tests
│   └── ...                       # Existing SDK tests
│
└── pyproject.toml                # Updated with service extras
```

---

## Implementation Tasks

### Phase 1: Core Service Skeleton

#### Task 1: FastAPI App Factory + Config

**Files:**
- Create: `service/__init__.py`
- Create: `service/app.py`
- Create: `service/config.py`
- Create: `service/__main__.py`
- Modify: `pyproject.toml` (add service dependencies)

Set up the FastAPI application with pydantic-settings configuration. Config reads from environment variables with sensible defaults:

```python
# service/config.py
class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8787
    encryption_key: str = ""          # Fernet key for credential storage
    db_path: str = "data/ftservice.db"
    api_key_required: bool = True
    auto_reauth: bool = True
    session_keepalive_interval: int = 300  # seconds
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="FTSERVICE_")
```

App factory creates the FastAPI instance, registers routes, and starts background tasks.

Entry point: `python -m service` or `uvicorn service.app:create_app --factory`

New pyproject.toml extras:
```toml
[project.optional-dependencies]
service = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "cryptography>=43.0",
    "aiosqlite>=0.20",
]
```

#### Task 2: Session Manager

**Files:**
- Create: `service/session/manager.py`
- Create: `service/session/store.py`
- Create: `service/dependencies.py`

The session manager wraps `FidelityClient` and adds lifecycle management:

```python
class SessionManager:
    """Manages FidelityClient instances and their lifecycle."""

    async def login(self, username, password, totp_secret=None) -> SessionStatus
    async def logout(self) -> None
    async def get_client(self) -> FidelityClient  # raises if not authenticated
    async def extend_session(self) -> bool
    async def status(self) -> SessionStatus

    @property
    def is_authenticated(self) -> bool
```

The store handles SQLite persistence for credentials (encrypted) and session metadata. Uses `cryptography.fernet.Fernet` for credential encryption.

FastAPI dependency injection:

```python
async def get_session(manager: SessionManager = Depends(get_manager)) -> FidelityClient:
    client = await manager.get_client()
    if client is None:
        raise HTTPException(401, detail={"code": "AUTH_REQUIRED"})
    return client
```

#### Task 3: API Key Auth

**Files:**
- Create: `service/auth/api_key.py`
- Create: `service/auth/middleware.py`

API key stored as SHA-256 hash in SQLite. Generated via CLI or `/service/api-key` endpoint on first run.

Middleware checks `Authorization: Bearer <key>` on all routes except `/health` and `/auth/login` (when in pass-through mode). Skipped entirely when `api_key_required=False` (local-only mode).

#### Task 4: Response Envelope + Error Handling

**Files:**
- Create: `service/models/responses.py`
- Create: `service/models/requests.py`

Consistent response wrapper and global exception handlers that catch SDK exceptions and map them to service error codes:

```python
FidelityError        → 502 FIDELITY_ERROR
AuthenticationError  → 401 AUTH_REQUIRED
SessionExpiredError  → 401 SESSION_EXPIRED
CSRFTokenError       → 502 FIDELITY_ERROR
APIError             → 502 FIDELITY_ERROR
httpx.HTTPStatusError → 502 FIDELITY_ERROR
```

### Phase 2: REST Endpoint Routes

#### Task 5: Auth Routes

**Files:**
- Create: `service/routes/auth.py`

```
POST /auth/login         → SessionManager.login()
POST /auth/login/totp    → SessionManager.submit_totp()
POST /auth/logout        → SessionManager.logout()
GET  /auth/status        → SessionManager.status()
POST /auth/credentials   → Store.save_credentials()
DELETE /auth/credentials → Store.delete_credentials()
```

#### Task 6: Account & Portfolio Routes

**Files:**
- Create: `service/routes/accounts.py`

Thin wrappers — each route gets the `FidelityClient` via dependency injection, calls the corresponding SDK method, and returns the Pydantic model (FastAPI serializes it automatically).

```python
@router.get("/{acct}/positions")
async def get_positions(acct: str, client: FidelityClient = Depends(get_session)):
    result = client.positions.get_positions([acct])
    return {"ok": True, "data": result.model_dump(by_alias=True)}
```

All 8 portfolio endpoints follow this pattern.

#### Task 7: Order Routes

**Files:**
- Create: `service/routes/orders.py`

Order routes need request body validation. The service accepts a simplified JSON body and constructs the SDK's `EquityOrderRequest` / `OptionOrderRequest` internally:

```json
POST /orders/equity/preview
{
  "account": "Z12345678",
  "symbol": "AAPL",
  "action": "buy",
  "quantity": 10,
  "order_type": "limit",
  "limit_price": 150.00,
  "time_in_force": "day"
}
```

Maps `"buy"` → `"B"`, `"limit"` → `"L"`, `"day"` → `"D"`, etc. The service translates human-readable values to Fidelity's internal codes.

#### Task 8: Market Data, Research, Watchlists, Preferences Routes

**Files:**
- Create: `service/routes/market_data.py`
- Create: `service/routes/research.py`
- Create: `service/routes/watchlists.py`
- Create: `service/routes/preferences.py`
- Create: `service/routes/service.py`

Straightforward SDK delegation. These are all read-only (except preferences save/delete) and follow the same pattern as portfolio routes.

### Phase 3: Streaming

#### Task 9: MDDS Connection Manager

**Files:**
- Create: `service/streaming/manager.py`

Background asyncio task that:
1. Maintains a single MDDS WebSocket connection using session cookies from `FidelityClient`
2. Tracks active symbol subscriptions (refcounted — unsubscribes only when last consumer drops)
3. Parses incoming messages via `MDDSClient.parse_message()`
4. Distributes parsed quotes to registered consumer callbacks
5. Handles reconnection on disconnect (exponential backoff)
6. Handles session re-auth (re-login and reconnect with new cookies)

```python
class MDDSManager:
    async def start(self, client: FidelityClient) -> None
    async def stop(self) -> None
    async def subscribe(self, symbols: list[str], callback: Callable) -> str  # returns subscription ID
    async def unsubscribe(self, subscription_id: str) -> None
    def get_subscriptions(self) -> dict[str, int]  # symbol → consumer count
```

#### Task 10: SSE + WebSocket Endpoints

**Files:**
- Create: `service/streaming/sse.py`
- Create: `service/streaming/ws.py`
- Create: `service/routes/streaming.py`

SSE endpoint (`GET /streaming/quotes?symbols=AAPL,TSLA`):
```
event: quote
data: {"symbol": "AAPL", "last": 195.23, "bid": 195.20, "ask": 195.25, ...}

event: quote
data: {"symbol": "TSLA", "last": 178.50, ...}
```

WebSocket endpoint (`WS /ws/quotes`):
- Client sends subscribe/unsubscribe JSON messages
- Server pushes quote JSON messages
- Ping/pong for keepalive

REST control endpoints:
```
POST /streaming/subscribe    {"symbols": ["AAPL", "TSLA"]}
POST /streaming/unsubscribe  {"symbols": ["AAPL"]}
GET  /streaming/subscriptions
```

### Phase 4: Session Keep-Alive + Auto-Reauth

#### Task 11: Background Keep-Alive

**Files:**
- Create: `service/session/keepalive.py`

Background task that periodically calls the session extend endpoint (backlog item 1.7: `GET /ftgw/digital/portfolio/extendsession`). Runs every `session_keepalive_interval` seconds (default 300 = 5 min).

If extension fails (session expired), and `auto_reauth=True` with stored credentials, automatically re-authenticates.

Emits events on session state changes so the streaming manager can reconnect.

### Phase 5: Docker + Deployment

#### Task 12: Docker Packaging

**Files:**
- Create: `docker/Dockerfile`
- Create: `docker/docker-compose.yml`
- Create: `docker/.env.example`

Multi-stage Dockerfile:
```dockerfile
# Build stage
FROM python:3.12-slim AS build
COPY . /app
RUN pip install /app[service]

# Runtime stage
FROM python:3.12-slim
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin/uvicorn /usr/local/bin/
COPY service/ /app/service/
WORKDIR /app
EXPOSE 8787
CMD ["python", "-m", "service"]
```

Docker Compose:
```yaml
services:
  fidelity-trader:
    build: .
    ports:
      - "8787:8787"
    volumes:
      - ./data:/app/data          # SQLite persistence
    env_file: .env
    restart: unless-stopped
```

`.env.example`:
```env
FTSERVICE_HOST=0.0.0.0
FTSERVICE_PORT=8787
FTSERVICE_ENCRYPTION_KEY=           # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FTSERVICE_API_KEY_REQUIRED=true
FTSERVICE_AUTO_REAUTH=true
FTSERVICE_LOG_LEVEL=INFO
```

#### Task 13: CLI Setup Command

**Files:**
- Create: `service/cli.py`

One-time setup wizard:
```bash
python -m service setup
```

1. Generates encryption key (if not set)
2. Generates API key
3. Optionally stores Fidelity credentials
4. Creates `data/` directory and SQLite database
5. Prints the config summary and next steps

---

## Phase Summary

| Phase | Tasks | What It Delivers |
|-------|-------|------------------|
| **1: Skeleton** | 1-4 | Running FastAPI app with auth, session management, config |
| **2: REST** | 5-8 | All 23 SDK modules exposed as REST endpoints |
| **3: Streaming** | 9-10 | Real-time quote streaming via SSE/WebSocket |
| **4: Keep-Alive** | 11 | Unattended long-running operation |
| **5: Docker** | 12-13 | One-command deployment on Linux |

Phases are sequential — each builds on the previous. Phase 1-2 delivers a usable REST service. Phase 3 adds real-time streaming. Phase 4-5 makes it production-ready for unattended use.

---

## Future Considerations

These are **not in scope** for the initial implementation but worth noting:

- **Scheduled orders** — Place orders at market open, or at a specific time
- **Webhook callbacks** — POST to a URL when an order fills, a price target hits, etc.
- **Portfolio snapshots** — Periodic position/balance snapshots stored in SQLite for historical tracking
- **Multi-account dashboard** — Aggregate view across all accounts
- **TLS termination** — Built-in HTTPS via Let's Encrypt for non-local deployments
- **OpenAPI spec export** — FastAPI generates this automatically, but it could be published for client generation in other languages
- **Rate limiting** — Protect against excessive Fidelity API calls (they may rate-limit or block)
