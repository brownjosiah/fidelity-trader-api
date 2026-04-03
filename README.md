# Fidelity Trader API

**Your Fidelity account, your API.**

Unofficial Python SDK, CLI, and self-hosted REST service for the Fidelity Trader+ API. Built by reverse-engineering network traffic from the Fidelity Trader+ desktop application via mitmproxy captures.

> **Disclaimer:** This is an unofficial, community-driven project. It is not affiliated with, endorsed by, or supported by Fidelity Investments. Use at your own risk. Trading involves risk of financial loss. By using this software, you accept full responsibility for any trades placed through your account.

[![Tests](https://github.com/brownjosiah/fidelity-trader-api/actions/workflows/ci.yml/badge.svg)](https://github.com/brownjosiah/fidelity-trader-api/actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
  - [CLI (Fastest)](#cli-fastest)
  - [Python SDK](#python-sdk)
  - [REST Service](#rest-service)
- [Installation](#installation)
- [Safety: Dry-Run Mode](#safety-dry-run-mode)
- [CLI Reference](#cli-reference)
- [SDK Reference](#sdk-reference)
  - [Authentication](#authentication)
  - [Portfolio](#portfolio)
  - [Trading](#trading)
  - [Market Data](#market-data)
  - [Research](#research)
  - [Watchlists & Alerts](#watchlists--alerts)
  - [Real-Time Streaming](#real-time-streaming)
  - [Session Management](#session-management)
- [REST Service](#rest-service-1)
  - [Endpoints](#endpoints)
  - [Streaming (SSE / WebSocket)](#streaming-sse--websocket)
  - [Docker Deployment](#docker-deployment)
- [Credential Providers](#credential-providers)
- [Error Handling](#error-handling)
- [Architecture](#architecture)
- [API Modules](#api-modules)
- [Development](#development)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

- **31 API modules** covering portfolio, trading, market data, research, streaming, alerts, and more
- **CLI tool (`ft`)** with 17 commands — positions, trading, quotes, streaming, all from your terminal
- **Self-hosted REST service** — 57 endpoints via FastAPI, Docker-ready, language-agnostic
- **Dry-run safety** — order placement defaults to preview-only; live trading requires explicit opt-in
- **Real-time WebSocket streaming** via Fidelity's MDDS protocol (live quotes, options with Greeks, 25-level L2 depth)
- **Full order lifecycle** — preview, place, cancel, and modify equity, single-leg option, multi-leg option, and conditional orders
- **Pydantic v2 models** for all API responses with type-safe field access
- **Credential providers** — AWS Secrets Manager, SSM Parameter Store, environment variables
- **Async client** via `AsyncFidelityClient` (wraps sync SDK with `asyncio.to_thread`)
- **Retry transport** with exponential backoff for transient failures
- **Auto session refresh** — background keep-alive for long-running applications
- **1587 tests** with full HTTP mocking via respx

## Quick Start

### CLI (Fastest)

```bash
pip install fidelity-trader-api[cli]

# Login (prompts for credentials, or reads FIDELITY_USERNAME / FIDELITY_PASSWORD env vars)
ft login

# See your positions
ft positions

# Get a quote
ft quote AAPL TSLA

# Preview a trade (dry-run by default — no order placed)
ft buy AAPL 10 --limit 150.00

# Stream live quotes
ft stream AAPL TSLA NVDA
```

### Python SDK

```python
from fidelity_trader import FidelityClient

with FidelityClient() as client:
    client.login(username="your_username", password="your_password")

    # Discover accounts
    accounts = client.accounts.discover_accounts()
    acct_nums = [a.acct_num for a in accounts.accounts]

    # Get positions
    positions = client.positions.get_positions(acct_nums)
    for acct in positions.accounts:
        for p in acct.positions:
            print(f"{p.symbol}: {p.quantity} shares @ ${p.price_detail.last_price}")

    # Get balances
    balances = client.balances.get_balances(acct_nums)
```

### REST Service

```bash
pip install fidelity-trader-api[service]

# Start the service
python -m service

# Or with Docker
docker compose -f docker/docker-compose.yml up -d

# Login
curl -X POST http://localhost:8787/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "...", "password": "..."}'

# Get positions
curl http://localhost:8787/api/v1/accounts/Z12345678/positions
```

## Installation

```bash
pip install fidelity-trader-api
```

### Extras

| Extra | Install | What it adds |
|-------|---------|-------------|
| `cli` | `pip install fidelity-trader-api[cli]` | `ft` command-line tool (typer + rich) |
| `service` | `pip install fidelity-trader-api[service]` | FastAPI REST service + Docker support |
| `aws` | `pip install fidelity-trader-api[aws]` | AWS Secrets Manager / SSM credential providers |
| `dev` | `pip install fidelity-trader-api[dev]` | Testing (pytest, respx, boto3) |

**Requirements:** Python 3.10+ and a Fidelity brokerage account with Trader+ access.

## Safety: Dry-Run Mode

**All order placement is blocked by default.** This prevents accidental trades when developing or testing.

| Context | Default | How to enable live trading |
|---------|---------|---------------------------|
| **SDK** | `live_trading=False` | `FidelityClient(live_trading=True)` or `FIDELITY_LIVE_TRADING=true` env var |
| **CLI** | Preview-only | Add `--live` flag: `ft buy AAPL 10 --limit 150 --live` |
| **Service** | Preview-only | Set `FTSERVICE_LIVE_TRADING=true` env var |

In dry-run mode:
- `preview_*` methods work normally
- `place_*` methods raise `DryRunError`
- The CLI shows the preview result and prints "Dry-run mode. Add --live to place this order."
- Cancellation is never blocked (you can always cancel orders)

---

## CLI Reference

The `ft` command-line tool provides 17 commands for interacting with your Fidelity account.

### Authentication

```bash
ft login                          # Interactive login (prompts or reads env vars)
ft login --username X --password Y  # Non-interactive
ft logout                         # Clear saved session
ft status                         # Check session health
```

Sessions are saved to `~/.config/ft/session.json` (Linux/Mac) or `%APPDATA%/ft/session.json` (Windows) and persist across commands. Sessions expire after ~30 minutes of inactivity.

### Portfolio

```bash
ft accounts                       # List all accounts
ft positions                      # Positions (auto-selects account if only one)
ft positions Z12345678             # Positions for specific account
ft balances                       # Account balances
```

### Trading

```bash
# Equity orders (preview by default)
ft buy AAPL 10                    # Market buy — preview only
ft buy AAPL 10 --limit 150.00    # Limit buy — preview only
ft sell TSLA 5 --stop 200.00     # Stop sell — preview only
ft buy AAPL 10 --limit 150 --live  # Actually place the order
ft buy AAPL 10 --limit 150 --live --yes  # Skip confirmation prompt

# Order management
ft orders                         # List open/recent orders
ft cancel CONF123                 # Cancel an order (always works, not gated)

# Options
ft options chain AAPL             # Option chain
ft options buy AAPL250418C00170000 1 --limit 3.50  # Buy call — preview
ft options sell AAPL250418P00160000 1 --live        # Sell put — live
```

### Market Data & Research

```bash
ft quote AAPL TSLA NVDA           # Quick quotes
ft chart AAPL --bars D --days 30  # Historical OHLCV
ft search "apple"                 # Symbol search
ft earnings AAPL MSFT             # Earnings data
ft dividends KO PG               # Dividend data
```

### Streaming

```bash
ft stream AAPL TSLA               # Live streaming quotes (updates in-place)
ft stream AAPL --fields last,bid,ask,volume  # Custom fields
```

### Output Formats

All commands support `--format json` for piping:

```bash
ft positions --format json | jq '.[] | select(.symbol == "AAPL")'
ft quote AAPL --format json
```

---

## SDK Reference

### Authentication

```python
from fidelity_trader import FidelityClient

# Basic login
with FidelityClient() as client:
    client.login(username="your_username", password="your_password")

# With TOTP 2FA
with FidelityClient() as client:
    client.login(
        username="your_username",
        password="your_password",
        totp_secret="YOUR_BASE32_TOTP_SECRET",
    )
```

The login is a 7-step handshake against `ecaap.fidelity.com`:

1. `GET /prgw/digital/login/atp` — Initialize login, set `SESSION_SCTX` cookie
2. `DELETE /user/session/login` — Clear stale sessions
3. `GET /user/identity/remember/username` — Check remembered user
4. `POST /user/identity/remember/username/1` — Select user, obtain `ET` token
5. `POST /user/factor/password/authentication` — Submit credentials
6. `PUT /user/identity/remember/username` — Update remembered user state
7. `POST /user/session/login` — Create session (sets `ATC`, `FC`, `RC`, `SC` cookies)

### Portfolio

```python
# Account discovery
accounts = client.accounts.discover_accounts()

# Positions
positions = client.positions.get_positions(["Z12345678"])

# Balances (includes margin details)
balances = client.balances.get_balances(["Z12345678"])

# Option positions summary
options = client.option_summary.get_option_summary(["Z12345678"])

# Transaction history
transactions = client.transactions.get_transaction_history(["Z12345678"], from_date, to_date)

# Closed positions (gain/loss)
closed = client.closed_positions.get_closed_positions(["Z12345678"], start_date, end_date)

# Loaned securities (fully paid lending rates)
loaned = client.loaned_securities.get_loaned_securities(["Z12345678"])

# Tax lot details
lots = client.tax_lots.get_tax_lots("Z12345678", "AAPL")
```

### Trading

All orders follow a **preview-then-place** workflow. Place methods are blocked by default (dry-run mode).

```python
from fidelity_trader.models.equity_order import EquityOrderRequest

# Enable live trading
with FidelityClient(live_trading=True) as client:
    client.login(username, password)

    # Build equity order
    order = EquityOrderRequest(
        acctNum="Z12345678",
        symbol="AAPL",
        orderActionCode="B",       # B=Buy, S=Sell
        qty=10,
        priceTypeCode="L",         # L=Limit, M=Market, S=Stop
        limitPrice=150.00,
        tifCode="D",               # D=Day, G=GTC
    )

    # Preview
    preview = client.equity_orders.preview_order(order)
    print(f"Estimated cost: {preview.estimated_cost}")

    # Place
    result = client.equity_orders.place_order(order, preview.conf_num)
    print(f"Order accepted: {result.is_accepted}")
```

**Single-leg options:**
```python
from fidelity_trader.models.single_option_order import SingleOptionOrderRequest

order = SingleOptionOrderRequest(
    acctNum="Z12345678",
    symbol="AAPL250418C00170000",
    orderActionCode="BC",          # BC=Buy Call, BP=Buy Put, SC=Sell Call, SP=Sell Put
    qty=1,
)
preview = client.single_option_orders.preview_order(order)
result = client.single_option_orders.place_order(order, preview.conf_num)
```

**Multi-leg options, cancel-and-replace, conditional orders** — see `examples/full_walkthrough.py`.

**Order management:**
```python
# Check order status
status = client.order_status.get_order_status(["Z12345678"])

# Cancel an order (not gated by dry-run)
client.cancel_order.cancel_order(conf_num="CONF123", acct_num="Z12345678", action_code="B")

# Staged/saved orders
staged = client.staged_orders.get_staged_orders(["Z12345678"])
```

### Market Data

```python
# Option chain
chain = client.option_chain.get_option_chain("AAPL")

# Depth of market (per-exchange quotes)
montage = client.option_chain.get_montage("AAPL")

# Historical chart data
chart = client.chart.get_chart("AAPL")

# Available markets
markets = client.available_markets.get_available_markets("AAPL", ["Z12345678"])

# Holiday calendar
holidays = client.holiday_calendar.get_holiday_calendar()
```

### Research

```python
# Earnings and dividends
earnings = client.research.get_earnings(["AAPL", "MSFT"])
dividends = client.research.get_dividends(["AAPL", "KO"])

# Symbol search
results = client.search.autosuggest("AAPL")

# Option analytics
analytics = client.option_analytics.analyze_position("AAPL", legs)

# Stock screener (LiveVol)
scan = client.screener.execute_scan(scan_definition)
```

### Watchlists & Alerts

```python
# Watchlists
watchlists = client.watchlists.get_watchlists()
client.watchlists.save_watchlist(name, symbols)

# Alert subscription
alert = client.alerts.subscribe()

# Alert messages
messages = client.alerts.get_alerts()

# Price triggers
triggers = client.price_triggers.list_triggers("Z12345678")
client.price_triggers.create_trigger("Z12345678", "AAPL", "greaterThan", 200.00)
client.price_triggers.delete_trigger("Z12345678", trigger_id)
```

### Real-Time Streaming

```python
from fidelity_trader.streaming.mdds import MDDSClient, MDDS_URL

with FidelityClient() as client:
    client.login(username, password)
    cookie_str = "; ".join(f"{c.name}={c.value}" for c in client._http.cookies.jar)

    mdds = MDDSClient()
    # Connect, subscribe, and parse — see examples/live_streaming.py
```

**MDDS field coverage:**
- **Equities:** last, bid/ask, volume, change, open, high, low, close, 52wk range, market cap
- **Options:** all equity fields + delta, gamma, theta, vega, rho, implied volatility, open interest
- **Time & Sales:** last trade price, size, time, exchange, condition, tick direction
- **L2 Depth:** 25-level order book (bids/asks with price, size, exchange, time)

### Session Management

```python
# Auto-refresh (background thread, keeps session alive)
client.enable_auto_refresh(interval=300)  # every 5 minutes
client.disable_auto_refresh()

# Manual keep-alive
client.session_keepalive.extend_session()
client.session_keepalive.is_session_alive()  # True/False

# Async client
from fidelity_trader import AsyncFidelityClient

async with AsyncFidelityClient() as client:
    await client.login(username, password)
    positions = await client.get_positions(["Z12345678"])

# Retry on transient failures
with FidelityClient(max_retries=3, retry_delay=1.0) as client:
    ...  # Retries on 429, 500, 502, 503, 504 with exponential backoff
```

---

## REST Service

The service wraps all 31 SDK modules as REST endpoints with session lifecycle management, streaming fan-out, and Docker deployment.

```bash
pip install fidelity-trader-api[service]
python -m service  # Starts on http://localhost:8787
```

### Configuration

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

### Endpoints

**Auth & Session:**
```
POST   /api/v1/auth/login              Login with Fidelity credentials
POST   /api/v1/auth/logout             Logout and clear session
GET    /api/v1/auth/status             Session state
POST   /api/v1/auth/credentials        Store encrypted credentials
DELETE /api/v1/auth/credentials        Remove stored credentials
```

**Accounts & Portfolio (8 endpoints):**
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

**Orders (13 endpoints):**
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

### Response Format

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

### Streaming (SSE / WebSocket)

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

### Docker Deployment

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

---

## Credential Providers

Avoid hardcoding credentials:

```python
from fidelity_trader.credentials import (
    EnvProvider,             # FIDELITY_USERNAME, FIDELITY_PASSWORD env vars
    SecretsManagerProvider,  # AWS Secrets Manager
    SSMParameterProvider,    # AWS SSM Parameter Store
    FileProvider,            # JSON file
    DirectProvider,          # Direct (testing only)
)

creds = EnvProvider().get_credentials()
# or: SecretsManagerProvider(secret_name="fidelity/trader").get_credentials()
# or: SSMParameterProvider(prefix="/fidelity/trader").get_credentials()

with FidelityClient() as client:
    client.login(creds.username, creds.password, totp_secret=creds.totp_secret)
```

## Error Handling

```python
from fidelity_trader import (
    FidelityError,          # Base exception
    AuthenticationError,    # Login failed
    SessionExpiredError,    # Session cookies expired
    CSRFTokenError,         # CSRF token error
    APIError,               # API error (has .status_code, .response_body)
    DryRunError,            # Order blocked by dry-run mode
)
```

## Architecture

All 31 API modules share a single `httpx.Client` instance via `FidelityClient`. Cookies (the auth mechanism) propagate automatically.

```
FidelityClient
├── _http: httpx.Client              shared cookie jar
├── _auth: AuthSession               7-step login + CSRF
├── 8 portfolio modules              positions, balances, accounts, ...
├── 8 order modules                  equity, option, cancel, conditional, ...
├── 2 market data modules            fastquote (chains + montage), chart
├── 4 research modules               earnings, search, analytics, screener
├── 3 streaming modules              MDDS quotes + L2, news auth
├── watchlists, alerts, price_triggers, preferences
├── available_markets, holiday_calendar, security_context
├── session_keepalive, auto_refresh
└── close()
```

## API Modules

| # | Accessor | Endpoint | Host |
|---|----------|----------|------|
| 1 | `positions` | `POST /ftgw/dp/position/v2` | dpservice |
| 2 | `balances` | `POST /ftgw/dp/balance/detail/v2` | dpservice |
| 3 | `accounts` | `POST /ftgw/dp/customer-am-acctnxt/v2/accounts` | dpservice |
| 4 | `option_summary` | `POST /ftgw/dp/retail-am-optionsummary/v1` | dpservice |
| 5 | `transactions` | `POST /ftgw/dp/accountmanagement/transaction/history/v2` | dpservice |
| 6 | `closed_positions` | `POST /ftgw/dp/customer-am-position/v1/.../closedposition` | dpservice |
| 7 | `loaned_securities` | `POST /ftgw/dp/retail-am-loanedsecurities/v1/.../rates` | dpservice |
| 8 | `tax_lots` | `POST /ftgw/dp/orderentry/taxlot/v1` | dpservice |
| 9 | `order_status` | `POST /ftgw/dp/retail-order-status/v3` | dpservice |
| 10 | `equity_orders` | `POST /ftgw/dp/orderentry/equity/{preview,place}/v1` | dpservice |
| 11 | `single_option_orders` | `POST /ftgw/dp/orderentry/option/{preview,place}/v2` | dpservice |
| 12 | `option_orders` | `POST /ftgw/dp/orderentry/multilegoption/{preview,place}/v1` | dpservice |
| 13 | `cancel_order` | `POST /ftgw/dp/orderentry/cancel/place/v1` | dpservice |
| 14 | `cancel_replace` | `POST /ftgw/dp/orderentry/cancelandreplace/{preview,place}/v1` | dpservice |
| 15 | `conditional_orders` | `POST /ftgw/dp/orderentry/conditional/{preview,place}/v1` | dpservice |
| 16 | `staged_orders` | `POST /ftgw/dp/ent-research-staging/v1/.../staged-order/get` | dpservice |
| 17 | `option_chain` | `GET fastquote/service/quote/{chainLite,dtmontage}` | fastquote |
| 18 | `chart` | `GET fastquote/service/marketdata/historical/chart/json` | fastquote |
| 19 | `research` | `GET /ftgw/dpdirect/research/{earning,dividend}/v1` | dpservice |
| 20 | `search` | `GET /ftgw/dpdirect/search/autosuggest/v1` | dpservice |
| 21 | `option_analytics` | `POST /ftgw/dp/research/option/positions/analytics/v1` | dpservice |
| 22 | `screener` | `POST fidelity.apps.livevol.com ExecuteScan` | livevol |
| 23 | `streaming` | `POST streaming-news/ftgw/snaz/Authorize` | streaming-news |
| 24 | `watchlists` | `POST /ftgw/dp/retail-watchlist/v1/.../get` | dpservice |
| 25 | `alerts` | `POST ecawsgateway/ftgw/alerts/services/ATBTSubscription` | ecawsgateway |
| 26 | `price_triggers` | `GET+POST /ftgw/dp/retail-price-triggers/v1` | dpservice |
| 27 | `preferences` | `POST /ftgw/dp/.../atn-prefs/{get,save,delete}preference` | dpservice |
| 28 | `available_markets` | `POST /ftgw/dp/reference/security/stock/availablemarket/v1` | dpservice |
| 29 | `holiday_calendar` | `GET /ftgw/dpdirect/market/holidaycalendar/v1` | dpservice |
| 30 | `security_context` | `POST /ftgw/digital/pico/api/v1/context/security` | digital |
| 31 | `session_keepalive` | `GET /ftgw/digital/portfolio/extendsession` | digital |

**MDDS WebSocket** (`wss://mdds-i-tc.fidelity.com`) — real-time quotes, options with Greeks, T&S, 25-level L2 depth.

## Development

```bash
git clone https://github.com/brownjosiah/fidelity-trader-api.git
cd fidelity-trader-api
pip install -e ".[dev,cli,service]"

# Run tests
pytest                              # all 1587 tests
pytest tests/test_positions.py -v   # single module
pytest --cov=fidelity_trader        # with coverage

# Lint
ruff check src/ service/ tests/
```

### Adding New API Modules

This SDK is built from captured network traffic. The workflow:

1. Start mitmproxy: `mitmweb --listen-port 8080 -w ~/capture.flow`
2. Route Trader+ through the proxy (system proxy + CA cert)
3. Perform the target action in Trader+
4. Analyze the capture: extract endpoints, request/response shapes
5. Create Pydantic model, API module, client integration, and tests

See [`docs/BACKLOG.md`](docs/BACKLOG.md) for the full backlog.

## Project Structure

```
fidelity-trader-api/
├── src/fidelity_trader/           # Python SDK (pip install)
│   ├── client.py                  # FidelityClient — composes all 31 modules
│   ├── async_client.py            # AsyncFidelityClient wrapper
│   ├── _http.py                   # HTTP session factory, base URLs, headers
│   ├── exceptions.py              # Exception hierarchy + DryRunError
│   ├── retry.py                   # RetryTransport with exponential backoff
│   ├── credentials.py             # Credential providers (AWS, env, file)
│   ├── cli/                       # CLI tool (ft command, 14 files)
│   ├── auth/                      # Authentication (login, 2FA, keepalive, auto-refresh)
│   ├── portfolio/                 # 8 portfolio modules
│   ├── orders/                    # 8 order modules
│   ├── market_data/               # Charts, option chains, montage
│   ├── research/                  # Earnings, dividends, search, analytics, screener
│   ├── streaming/                 # MDDS WebSocket (quotes, L2, T&S) + news auth
│   ├── watchlists/                # Watchlist get/save
│   ├── alerts/                    # Alert subscription + price triggers
│   ├── settings/                  # User preferences
│   ├── reference/                 # Available markets, holiday calendar
│   └── models/                    # 25+ Pydantic response models
│
├── service/                       # FastAPI REST service
│   ├── app.py                     # App factory, exception handlers, lifespan
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── dependencies.py            # FastAPI dependency injection
│   ├── auth/                      # API key generation + middleware
│   ├── session/                   # Session manager, credential store, keepalive
│   ├── streaming/                 # MDDS fan-out, SSE, WebSocket
│   ├── routes/                    # 9 route files (57 endpoints)
│   └── models/                    # Request/response schemas
│
├── docker/                        # Docker deployment
│   ├── Dockerfile                 # Multi-stage build
│   ├── docker-compose.yml         # One-command deployment
│   └── .env.example               # Environment template
│
├── tests/                         # 1587 tests
├── examples/                      # Usage examples
└── docs/                          # BACKLOG, SERVICE_PLAN, DECISIONS, PRODUCT_VISION
```

## Roadmap

The SDK, CLI, and service are feature-complete for the MVP. Remaining work:

| Priority | Items |
|----------|-------|
| **Medium** | Watchlist CRUD, Alerts CRUD, full priced option chain, news WebSocket, fundamentals, docs site, CI smoke tests |
| **Low** | TypeScript/Go clients (from OpenAPI), HashiCorp Vault provider, MDDS reconnect, contribution guide |

See [`docs/BACKLOG.md`](docs/BACKLOG.md) for the full backlog and [`docs/PRODUCT_VISION.md`](docs/PRODUCT_VISION.md) for product strategy.

## License

Apache 2.0 — see [LICENSE](LICENSE).
