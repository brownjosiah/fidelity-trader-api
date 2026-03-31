# Fidelity Trader SDK

Unofficial Python SDK for the Fidelity Trader+ API. Built by reverse-engineering network traffic from the Fidelity Trader+ desktop application via mitmproxy captures.

> **Disclaimer:** This is an unofficial, community-driven project. It is not affiliated with, endorsed by, or supported by Fidelity Investments. Use at your own risk. Trading involves risk of loss.

## Features

- **23 API modules** covering portfolio, trading, market data, research, streaming, and more
- **Real-time WebSocket streaming** via Fidelity's MDDS protocol (live quotes, options with Greeks, Time & Sales)
- **Full order lifecycle** — preview, place, monitor, and cancel equity and multi-leg option orders
- **Pydantic v2 models** for all API responses with type-safe field access
- **Multiple credential providers** — AWS Secrets Manager, SSM Parameter Store, environment variables, file, or direct
- **Cookie-based session management** with 7-step login handshake and optional TOTP 2FA
- **822 tests** with full HTTP mocking via respx

## Requirements

- Python 3.10+
- A Fidelity brokerage account with Trader+ access

## Installation

```bash
# From source (editable)
git clone https://github.com/brownjosiah/fidelity-trader-sdk.git
cd fidelity-trader-sdk
pip install -e .

# With dev dependencies (testing)
pip install -e ".[dev]"

# With AWS credential provider support
pip install -e ".[aws]"
```

### Optional Dependencies

| Extra | Packages | Purpose |
|-------|----------|---------|
| `aws` | `boto3>=1.34` | AWS Secrets Manager / SSM credential providers |
| `dev` | `pytest`, `respx`, `boto3` | Testing and development |

For real-time WebSocket streaming, also install:
```bash
pip install websockets
```

## Quick Start

```python
from fidelity_trader import FidelityClient

with FidelityClient() as client:
    # Authenticate
    client.login(username="your_username", password="your_password")

    # Discover accounts
    accounts = client.accounts.discover_accounts()
    acct_nums = [a.acct_num for a in accounts.accounts]

    # Get positions
    positions = client.positions.get_positions(acct_nums)
    for acct in positions.accounts:
        print(f"Account {acct.acct_num}: {len(acct.positions)} positions")
        for p in acct.positions:
            print(f"  {p.symbol}: {p.quantity} shares @ ${p.price_detail.last_price}")

    # Get balances
    balances = client.balances.get_balances(acct_nums)
    for b in balances.accounts:
        nw = b.recent_balance_detail.acct_val_detail.net_worth
        print(f"  {b.acct_num}: ${nw:,.2f}")
```

## Authentication

### Basic Login

```python
with FidelityClient() as client:
    client.login(username="your_username", password="your_password")
    print(client.is_authenticated)  # True
```

### Login with 2FA (TOTP)

If your account has two-factor authentication enabled:

```python
with FidelityClient() as client:
    client.login(
        username="your_username",
        password="your_password",
        totp_secret="YOUR_BASE32_TOTP_SECRET",
    )
```

The SDK generates and submits the TOTP code automatically using `pyotp`.

### Credential Providers

Avoid hardcoding credentials by using a credential provider:

```python
from fidelity_trader import FidelityClient
from fidelity_trader.credentials import (
    SecretsManagerProvider,  # AWS Secrets Manager
    SSMParameterProvider,    # AWS SSM Parameter Store
    EnvProvider,             # Environment variables
    FileProvider,            # JSON file
    DirectProvider,          # Direct (testing)
)

# AWS Secrets Manager (single JSON secret)
creds = SecretsManagerProvider(secret_name="fidelity/trader").get_credentials()

# AWS Secrets Manager (separate secrets)
creds = SecretsManagerProvider(
    username_secret="fidelity/username",
    password_secret="fidelity/password",
    totp_secret_name="fidelity/totp_secret",
).get_credentials()

# AWS SSM Parameter Store
creds = SSMParameterProvider(prefix="/fidelity/trader").get_credentials()

# Environment variables (FIDELITY_USERNAME, FIDELITY_PASSWORD)
creds = EnvProvider().get_credentials()

# JSON file ({"username": "...", "password": "..."})
creds = FileProvider(path="credentials.json").get_credentials()

# Use with client
with FidelityClient() as client:
    client.login(creds.username, creds.password, totp_secret=creds.totp_secret)
```

### Authentication Flow

The login is a 7-step handshake against `ecaap.fidelity.com`:

1. `GET /prgw/digital/login/atp` — Initialize login page, set `SESSION_SCTX` cookie
2. `DELETE /user/session/login` — Clear stale sessions
3. `GET /user/identity/remember/username` — Check remembered user
4. `POST /user/identity/remember/username/1` — Select remembered user, obtain `ET` token
5. `POST /user/factor/password/authentication` — Submit credentials
6. `PUT /user/identity/remember/username` — Update remembered user state
7. `POST /user/session/login` — Create authenticated session (sets `ATC`, `FC`, `RC`, `SC` cookies)

If 2FA is required (response code `1201`), an additional TOTP submission step runs automatically.

## API Reference

### Portfolio

```python
# Account discovery
accounts = client.accounts.discover_accounts()

# Positions
positions = client.positions.get_positions(["Z12345678"])

# Balances
balances = client.balances.get_balances(["Z12345678"])

# Option positions summary
options = client.option_summary.get_option_summary(["Z12345678"])

# Transaction history
transactions = client.transactions.get_transaction_history(
    ["Z12345678"],
    from_date=1710000000,  # Unix timestamp
    to_date=1710600000,
)

# Closed positions (gain/loss)
closed = client.closed_positions.get_closed_positions(
    ["Z12345678"],
    start_date="03/01/2026",
    end_date="03/31/2026",
)

# Loaned securities (fully paid lending rates)
loaned = client.loaned_securities.get_loaned_securities(["Z12345678"])

# Tax lot details
lots = client.tax_lots.get_tax_lots("Z12345678", "AAPL")
```

### Trading

#### Equity Orders

Orders follow a two-step preview-then-place workflow:

```python
from fidelity_trader.models.equity_order import EquityOrderRequest

# Build the order
order = EquityOrderRequest(
    acct_num="Z12345678",
    symbol="AAPL",
    order_action_code="B",       # "B"=Buy, "S"=Sell
    qty=10,
    price_type_code="L",         # "L"=Limit, "M"=Market
    limit_price=150.00,
    tif_code="D",                # "D"=Day, "G"=GTC
    acct_type_code="C",          # "C"=Cash, "M"=Margin
)

# Step 1: Preview (validates order, returns confirmation number)
preview = client.equity_orders.preview_order(order)
print(f"Estimated cost: {preview.estimated_cost}")
conf_num = preview.conf_num

# Step 2: Place (submits the order)
result = client.equity_orders.place_order(order, conf_num)
print(f"Order status: {result.resp_type_code}")  # "A" = Accepted
```

#### Multi-Leg Option Orders

```python
from fidelity_trader.models.option_order import OptionOrderRequest, OptionLeg

order = OptionOrderRequest(
    acct_num="Z12345678",
    strategy="VERTICAL",
    legs=[
        OptionLeg(symbol="AAPL260417C200", action="BTO", qty=1),
        OptionLeg(symbol="AAPL260417C210", action="STO", qty=1),
    ],
    price_type_code="N",         # "N"=Net debit/credit
    net_price=2.50,
    tif_code="D",
)

preview = client.option_orders.preview_order(order)
result = client.option_orders.place_order(order, preview.conf_num)
```

#### Order Management

```python
# Check order status
status = client.order_status.get_order_status(["Z12345678"])
for order in status.orders:
    print(f"{order.base_order_detail.description}: {order.status_detail.status_code}")

# Cancel an order
client.cancel_order.cancel_order(
    account_number="Z12345678",
    order_number="123456789",
)
```

### Market Data

```python
# Option chain (all expirations and strikes)
chain = client.option_chain.get_option_chain("AAPL")
for exp in chain.calls:
    print(f"Expiry {exp.date}: {len(exp.options)} strikes")

# Depth of market / montage (per-exchange bid/ask)
montage = client.option_chain.get_montage("AAPL260417C200")
for quote in montage.quotes:
    print(f"  {quote.exchange_name}: {quote.bid} x {quote.ask}")

# Historical chart data
chart = client.chart.get_chart("AAPL", period="1M", bar_size="1D")

# Available markets for a symbol
markets = client.available_markets.get_available_markets("AAPL", ["Z12345678"])
```

### Research

```python
# Earnings
earnings = client.research.get_earnings(["AAPL", "MSFT", "NVDA"])
for e in earnings.earnings:
    latest = e.quarters[-1]
    print(f"{e.sec_detail.symbol}: EPS={latest.adjusted_eps} (est={latest.consensus_est})")

# Dividends
dividends = client.research.get_dividends(["AAPL", "KO"])
for d in dividends.dividends:
    print(f"{d.sec_detail.symbol}: yield={d.yld_ttm}%, ex-date={d.ex_div_date}")

# Symbol search / autosuggest
results = client.search.autosuggest("AAPL")
for s in results.suggestions:
    print(f"{s.symbol}: {s.desc} ({s.type})")

# Option analytics (P/L, Greeks, probability)
analytics = client.option_analytics.analyze_position("AAPL", [
    {"symbol": "AAPL260417C200", "qty": 1, "price": 0, "equity": False},
    {"symbol": "AAPL260417C210", "qty": -1, "price": 0, "equity": False},
])
```

### Watchlists & Alerts

```python
# Get all watchlists
watchlists = client.watchlists.get_watchlists()
for wl in watchlists.watchlists:
    symbols = [s.symbol for s in wl.security_details]
    print(f"{wl.watchlist_name}: {symbols}")

# Subscribe to alerts
alert = client.alerts.subscribe()
print(f"Alert server: {alert.server_url}")

# User preferences
prefs = client.preferences.get_preferences("user/atn/global/v1")
client.preferences.save_preferences("user/atn/global/v1", {"DefaultAccountNumber": "Z12345678"})
client.preferences.delete_preferences("user/atn/layout/custom")
```

### Real-Time Streaming (MDDS WebSocket)

The SDK includes a client for Fidelity's MDDS WebSocket protocol, which provides real-time quotes, options with Greeks, and Time & Sales data.

```python
import json
import asyncio
import websockets
from fidelity_trader import FidelityClient
from fidelity_trader.streaming.mdds import MDDSClient, MDDS_URL

# Login first to establish session cookies
with FidelityClient() as client:
    client.login(username, password)
    cookie_str = "; ".join(f"{c.name}={c.value}" for c in client._http.cookies.jar)

    # Connect to MDDS WebSocket
    async def stream():
        async with websockets.connect(
            MDDS_URL,
            additional_headers={"Cookie": cookie_str},
        ) as ws:
            # Handle connection
            connect_msg = json.loads(await ws.recv())
            session_id = connect_msg["SessionId"]

            # Subscribe to symbols
            await ws.send(json.dumps({
                "SessionId": session_id,
                "Command": "subscribe",
                "Symbol": "AAPL,TSLA,.SPX",
                "ConflationRate": 1000,
                "IncludeGreeks": True,
            }))

            # Parse incoming quotes
            mdds = MDDSClient()
            async for msg in ws:
                quotes = mdds.parse_message(msg)
                for q in quotes:
                    print(f"{q.symbol}: ${q.last_price} bid=${q.bid} ask=${q.ask}")
                    if q.is_option:
                        print(f"  delta={q.delta}")
                    if q.has_trade_data:
                        print(f"  T&S: {q.last_trade_size}@{q.last_trade_price}")

    asyncio.run(stream())
```

**MDDS Field Coverage:**
- **Equities:** last price, bid/ask, volume, change, change%, open, high, low, close, 52wk high/low, market cap
- **Options:** all equity fields + delta, gamma, theta, vega, rho, implied volatility, open interest
- **Time & Sales:** last trade price, size, time, exchange, condition, tick direction, sequence

### Streaming News Auth

```python
# Get streaming news authorization token
stream = client.streaming.authorize()
print(f"Host: {stream.streaming_host}:{stream.streaming_port}")
print(f"Token: {stream.access_token}")
```

### Security Context

```python
# Query entitlements (called automatically during login)
ctx = client.security_context.get_context()
print(f"Real-time quotes: {ctx.has_realtime_quotes}")
print(f"ATP access: {ctx.has_atp_access}")
```

## API Modules

| # | Accessor | Class | Endpoint | Host |
|---|----------|-------|----------|------|
| 1 | `positions` | PositionsAPI | `POST /ftgw/dp/position/v2` | dpservice |
| 2 | `balances` | BalancesAPI | `POST /ftgw/dp/balance/detail/v2` | dpservice |
| 3 | `option_summary` | OptionSummaryAPI | `POST /ftgw/dp/retail-am-optionsummary/v1` | dpservice |
| 4 | `transactions` | TransactionsAPI | `POST /ftgw/dp/accountmanagement/transaction/history/v2` | dpservice |
| 5 | `order_status` | OrderStatusAPI | `POST /ftgw/dp/retail-order-status/v3` | dpservice |
| 6 | `equity_orders` | EquityOrderAPI | `POST /ftgw/dp/orderentry/equity/{preview,place}/v1` | dpservice |
| 7 | `option_orders` | MultiLegOptionOrderAPI | `POST /ftgw/dp/orderentry/multilegoption/{preview,place}/v1` | dpservice |
| 8 | `cancel_order` | OrderCancelAPI | `POST /ftgw/dp/orderentry/cancel/place/v1` | dpservice |
| 9 | `research` | ResearchAPI | `GET /ftgw/dpdirect/research/{earning,dividend}/v1` | dpservice |
| 10 | `search` | SearchAPI | `GET /ftgw/dpdirect/search/autosuggest/v1` | dpservice |
| 11 | `option_analytics` | OptionAnalyticsAPI | `POST /ftgw/dp/research/option/positions/analytics/v1` | dpservice |
| 12 | `option_chain` | FastQuoteAPI | `GET /service/quote/{chainLite,dtmontage}` | fastquote |
| 13 | `chart` | ChartAPI | `GET /service/marketdata/historical/chart/json` | fastquote |
| 14 | `streaming` | StreamingNewsAPI | `POST /ftgw/snaz/Authorize` | streaming-news |
| 15 | `watchlists` | WatchlistAPI | `POST /ftgw/dp/retail-watchlist/v1/.../get` | dpservice |
| 16 | `accounts` | AccountsAPI | `POST /ftgw/dp/customer-am-acctnxt/v2/accounts` | dpservice |
| 17 | `alerts` | AlertsAPI | `POST /ftgw/alerts/services/ATBTSubscription` | ecawsgateway |
| 18 | `closed_positions` | ClosedPositionsAPI | `POST /ftgw/dp/customer-am-position/v1/.../closedposition` | dpservice |
| 19 | `loaned_securities` | LoanedSecuritiesAPI | `POST /ftgw/dp/retail-am-loanedsecurities/v1/.../rates` | dpservice |
| 20 | `tax_lots` | TaxLotAPI | `POST /ftgw/dp/orderentry/taxlot/v1` | dpservice |
| 21 | `available_markets` | AvailableMarketsAPI | `POST /ftgw/dp/reference/security/stock/availablemarket/v1` | dpservice |
| 22 | `preferences` | PreferencesAPI | `POST /ftgw/dp/.../atn-prefs/{get,save,delete}preference` | dpservice |
| 23 | `security_context` | SecurityContextAPI | `POST /ftgw/digital/pico/api/v1/context/security` | digital |

**Hosts:**
| Host | Base URL | Purpose |
|------|----------|---------|
| dpservice | `https://dpservice.fidelity.com` | Portfolio, orders, research, watchlists, preferences |
| fastquote | `https://fastquote.fidelity.com` | Option chains, montage, charts |
| ecaap | `https://ecaap.fidelity.com` | Authentication (7-step login + TOTP 2FA) |
| digital | `https://digital.fidelity.com` | Login page, security context, session management |
| ecawsgateway | `https://ecawsgateway.fidelity.com` | Alerts (SOAP/XML) |
| streaming-news | `https://streaming-news.mds.fidelity.com` | News streaming authorization |
| mdds | `wss://mdds-i-tc.fidelity.com` | Real-time market data WebSocket |

## Project Structure

```
fidelity-trader-sdk/
├── src/fidelity_trader/
│   ├── __init__.py              # Package exports
│   ├── _http.py                 # HTTP session factory, base URLs, headers
│   ├── client.py                # FidelityClient — composes all 23 modules
│   ├── credentials.py           # Credential providers (AWS, env, file)
│   ├── exceptions.py            # Exception hierarchy
│   │
│   ├── auth/                    # Authentication
│   │   ├── session.py           # 7-step login handshake + TOTP 2FA
│   │   └── security_context.py  # Entitlements / real-time quote access
│   │
│   ├── portfolio/               # Account & position data
│   │   ├── accounts.py          # Account discovery
│   │   ├── positions.py         # Current positions
│   │   ├── balances.py          # Account balances
│   │   ├── option_summary.py    # Option positions summary
│   │   ├── transactions.py      # Transaction history
│   │   ├── closed_positions.py  # Closed position gain/loss
│   │   ├── loaned_securities.py # Fully paid lending rates
│   │   └── tax_lots.py          # Tax lot details
│   │
│   ├── orders/                  # Order management
│   │   ├── equity.py            # Equity order preview/place
│   │   ├── options.py           # Multi-leg option order preview/place
│   │   ├── status.py            # Order status monitoring
│   │   └── cancel.py            # Order cancellation
│   │
│   ├── market_data/             # Market data
│   │   ├── fastquote.py         # Option chains + depth of market
│   │   └── chart.py             # Historical chart data
│   │
│   ├── streaming/               # Real-time data
│   │   ├── mdds.py              # MDDS WebSocket client
│   │   ├── mdds_fields.py       # Field ID mapping + parsing
│   │   └── news.py              # News streaming auth
│   │
│   ├── research/                # Research data
│   │   ├── data.py              # Earnings + dividends
│   │   ├── search.py            # Symbol autosuggest
│   │   └── analytics.py         # Option position analytics
│   │
│   ├── watchlists/              # Watchlist management
│   │   └── watchlists.py
│   │
│   ├── alerts/                  # Alert subscriptions
│   │   └── subscription.py
│   │
│   ├── settings/                # User preferences
│   │   └── preferences.py
│   │
│   ├── reference/               # Reference data
│   │   └── markets.py           # Available markets/exchanges
│   │
│   └── models/                  # Pydantic response models (23 files)
│       ├── account.py, account_detail.py, position.py, balance.py
│       ├── equity_order.py, option_order.py, cancel_order.py, order.py
│       ├── fastquote.py, chart.py, option_summary.py, transaction.py
│       ├── closed_position.py, loaned_securities.py, tax_lot.py
│       ├── research.py, search.py, analytics.py, alerts.py
│       ├── watchlist.py, preferences.py, available_market.py
│       ├── streaming.py, security_context.py, and auth.py
│       └── ...
│
├── tests/                       # 822 tests
│   ├── conftest.py              # Shared fixtures
│   └── test_*.py                # One test file per module
│
├── examples/
│   ├── login.py                 # Minimal login example
│   ├── full_walkthrough.py      # All 23 modules demonstrated
│   ├── live_streaming.py        # Real-time MDDS WebSocket streaming
│   ├── live_test.py             # Live integration test
│   └── mdds_experiment.py       # MDDS protocol experiments
│
├── docs/
│   └── BACKLOG.md               # Project backlog and roadmap
│
└── pyproject.toml               # Build config (hatchling)
```

## Architecture

All 23 API modules share a single `httpx.Client` instance via the `FidelityClient` compositor. This ensures cookies (the authentication mechanism) are shared across all API calls automatically.

```
FidelityClient
├── _http: httpx.Client          ← shared across all modules
├── _auth: AuthSession           ← login/logout/CSRF
├── positions: PositionsAPI(_http)
├── balances: BalancesAPI(_http)
├── equity_orders: EquityOrderAPI(_http)
├── option_chain: FastQuoteAPI(_http)
├── ... (19 more modules)
└── close() / __exit__()         ← closes httpx.Client
```

Each API module follows the same pattern:

```python
class SomeAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_something(self, params) -> SomeResponse:
        resp = self._http.post(f"{DPSERVICE_URL}/endpoint", json=body)
        resp.raise_for_status()
        return SomeResponse.from_api_response(resp.json())
```

Response models use Pydantic v2 with `from_api_response()` class methods that flatten Fidelity's deeply nested JSON structures into clean, typed objects.

## Error Handling

```python
from fidelity_trader import (
    FidelityError,          # Base exception
    AuthenticationError,    # Login failed
    SessionExpiredError,    # Session cookies expired
    CSRFTokenError,         # Failed to obtain CSRF token
    APIError,               # API returned an error (includes status_code, response_body)
)

try:
    client.login(username, password)
except AuthenticationError as e:
    print(f"Login failed: {e}")

try:
    positions = client.positions.get_positions(accounts)
except SessionExpiredError:
    client.login(username, password)  # Re-authenticate
    positions = client.positions.get_positions(accounts)
except APIError as e:
    print(f"API error {e.status_code}: {e.response_body}")
```

## Development

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_positions.py -v

# With coverage
pytest --cov=fidelity_trader
```

### Adding New API Modules

This SDK is built from captured network traffic. The workflow for adding a new module:

1. **Capture traffic** — Start mitmproxy, route Trader+ through it, perform the target action
   ```bash
   mitmweb --listen-port 8080 -w ~/capture.flow
   ```

2. **Analyze the capture** — Filter and inspect the relevant endpoints
   ```bash
   mitmdump -n -r ~/capture.flow -s ~/fidelity_filter.py
   ```

3. **Create the model** — Add a Pydantic model in `src/fidelity_trader/models/` matching the response shape

4. **Create the API module** — Add the API class in the appropriate subdirectory

5. **Wire it up** — Add the module to `FidelityClient.__init__` in `client.py`

6. **Write tests** — Add tests with respx mocking in `tests/`

### Code Conventions

- **httpx** for all HTTP calls (not requests)
- **Pydantic v2** for all response models with `populate_by_name=True` and camelCase aliases
- **respx** for HTTP mocking in tests
- All modules receive the shared `httpx.Client` — never create their own
- Credentials never hardcoded — use credential providers
- Capture files (`*.flow`, `*.har`) are gitignored

## Roadmap

Development follows two phases. **Phase 1 (SDK completeness) must come first** — the service layer is only as useful as the SDK it wraps.

### Phase 1: Complete Trader+ API Coverage

The SDK currently covers 23 of Fidelity Trader+'s API modules. The remaining work focuses on capturing and implementing the missing endpoints to reach full parity with the desktop application.

**High priority — complete the trading workflow:**
- Single-leg option orders (preview + place)
- Order modification (change price/qty on open orders)
- Conditional/triggered orders (stop-loss, OCO, brackets)
- Level 2 streaming depth (real-time book data via MDDS)

**Medium priority — fill data gaps:**
- Watchlist CRUD (create, rename, delete — currently read-only)
- Alerts CRUD (create, edit, delete — currently subscribe-only)
- Full priced option chain (live bid/ask for all strikes)
- Margin/buying power details
- Stock/option screener
- Fundamentals and company data
- News WebSocket feed
- Market holiday calendar
- Session keep-alive for long-running bots

**Already captured, needs implementation:**
- Holiday calendar, staged orders, price triggers, session extend endpoint

See [`docs/BACKLOG.md`](docs/BACKLOG.md) for the full backlog with 32 items across 4 categories.

### Phase 2: Self-Hosted Service Layer

Once the SDK has sufficient Trader+ coverage, wrap it in a self-hosted REST/WebSocket service that any language or tool can consume:

- **FastAPI REST API** exposing all SDK modules as HTTP endpoints
- **Real-time streaming fan-out** — single MDDS connection, multiple consumers via SSE/WebSocket
- **Session management** — auto keep-alive, re-auth, encrypted credential storage
- **Docker deployment** — single `docker-compose up` on Linux
- **Language-agnostic** — call from Node, Go, Rust, shell scripts, or anything that speaks HTTP

See [`docs/SERVICE_PLAN.md`](docs/SERVICE_PLAN.md) for the full implementation plan.

## License

MIT
