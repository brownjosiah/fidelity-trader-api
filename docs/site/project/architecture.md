# Architecture

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
