# SDK Reference

## Authentication

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

## Portfolio

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

## Trading

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

## Market Data

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

## Research

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

## Watchlists & Alerts

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

## Real-Time Streaming

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

## Session Management

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
