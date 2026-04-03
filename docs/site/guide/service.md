# REST Service

The service wraps all 31 SDK modules as REST endpoints with session lifecycle management, streaming fan-out, and Docker deployment.

```bash
pip install fidelity-trader-api[service]
python -m service  # Starts on http://localhost:8787
```

## Configuration

All settings via environment variables with `FTSERVICE_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `FTSERVICE_HOST` | `127.0.0.1` | Bind address |
| `FTSERVICE_PORT` | `8787` | Port |
| `FTSERVICE_API_KEY_REQUIRED` | `true` | Require `Authorization: Bearer <key>` |
| `FTSERVICE_ENCRYPTION_KEY` | | Fernet key for credential storage |
| `FTSERVICE_LIVE_TRADING` | `false` | Enable live order placement |
| `FTSERVICE_AUTO_REAUTH` | `true` | Re-authenticate on session expiry |
| `FTSERVICE_SESSION_KEEPALIVE_INTERVAL` | `300` | Keep-alive interval (seconds) |
| `FTSERVICE_LOG_LEVEL` | `INFO` | Logging level |

## Endpoints

### Auth & Session

```
POST   /api/v1/auth/login              Login with Fidelity credentials
POST   /api/v1/auth/logout             Logout and clear session
GET    /api/v1/auth/status             Session state
POST   /api/v1/auth/credentials        Store encrypted credentials
DELETE /api/v1/auth/credentials        Remove stored credentials
```

### Accounts & Portfolio (8 endpoints)

```
GET    /api/v1/accounts                         All accounts
GET    /api/v1/accounts/{acct}/positions         Positions
GET    /api/v1/accounts/{acct}/balances          Balances
GET    /api/v1/accounts/{acct}/transactions      Transaction history
GET    /api/v1/accounts/{acct}/options-summary   Option positions
GET    /api/v1/accounts/{acct}/closed-positions  Closed positions
GET    /api/v1/accounts/{acct}/loaned-securities Loaned securities
GET    /api/v1/accounts/{acct}/tax-lots/{symbol} Tax lots
```

### Orders (13 endpoints)

```
GET    /api/v1/orders/status                     Open/recent orders
GET    /api/v1/orders/staged                     Staged orders
POST   /api/v1/orders/equity/preview             Preview equity order
POST   /api/v1/orders/equity/place               Place equity order
POST   /api/v1/orders/option/preview             Preview single-leg option
POST   /api/v1/orders/option/place               Place single-leg option
POST   /api/v1/orders/options/preview            Preview multi-leg option
POST   /api/v1/orders/options/place              Place multi-leg option
POST   /api/v1/orders/{conf_num}/cancel          Cancel order
POST   /api/v1/orders/replace/preview            Preview cancel-replace
POST   /api/v1/orders/replace/place              Place cancel-replace
POST   /api/v1/orders/conditional/preview        Preview conditional order
POST   /api/v1/orders/conditional/place          Place conditional order
```

**Market Data, Research, Watchlists, Preferences, Reference** — 19 more endpoints. See `/docs` for the full OpenAPI spec.

## Response Format

All responses use a consistent envelope:

```json
{"ok": true, "data": { ... }, "error": null}
```

Error responses:

```json
{"ok": false, "data": null, "error": {"code": "AUTH_REQUIRED", "message": "Not authenticated"}}
```

| Error Code | HTTP | Meaning |
|------------|------|---------|
| `AUTH_REQUIRED` | 401 | Not logged in |
| `SESSION_EXPIRED` | 401 | Session timed out |
| `LIVE_TRADING_DISABLED` | 403 | Dry-run mode active |
| `API_KEY_INVALID` | 403 | Bad or missing API key |
| `FIDELITY_ERROR` | 502 | Upstream Fidelity error |

## Streaming (SSE / WebSocket)

The service fans out a single MDDS WebSocket connection to multiple consumers:

**Server-Sent Events:**
```bash
curl -N "http://localhost:8787/api/v1/streaming/quotes?symbols=AAPL,TSLA"
# event: quote
# data: {"symbol": "AAPL", "last": 195.23, "bid": 195.20, "ask": 195.25}
```

**WebSocket:**
```javascript
const ws = new WebSocket("ws://localhost:8787/api/v1/ws/quotes");
ws.send(JSON.stringify({ action: "subscribe", symbols: ["AAPL", "TSLA"] }));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

**REST control:**
```
POST /api/v1/streaming/subscribe      {"symbols": ["AAPL"]}
POST /api/v1/streaming/unsubscribe    {"symbols": ["AAPL"]}
GET  /api/v1/streaming/subscriptions  Current subscriptions
GET  /api/v1/streaming/status         Connection state
```

## Docker Deployment

```bash
# Copy and edit environment config
cp docker/.env.example docker/.env
# Generate encryption key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Start
docker compose -f docker/docker-compose.yml up -d

# Health check
curl http://localhost:8787/health
```
