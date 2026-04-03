# Fidelity Trader API

## Project Overview
Unofficial Python SDK, CLI tool, and self-hosted REST service that replicates the Fidelity Trader+ desktop application's API calls. Built entirely by reverse-engineering network traffic via mitmproxy captures — no assumptions, no other repos.

**Package:** `fidelity-trader-api` on PyPI (import as `fidelity_trader`)
**31 SDK modules, 17 CLI commands, 57 service endpoints, 1587 tests, Python 3.10+**

## Architecture

Three layers — SDK (foundation), CLI (terminal), Service (REST API):

```
fidelity-trader-api/
├── src/fidelity_trader/           # Python SDK — all Fidelity protocol logic
│   ├── client.py                  # FidelityClient — composes all 31 modules
│   ├── async_client.py            # AsyncFidelityClient (asyncio.to_thread wrapper)
│   ├── _http.py                   # Base URLs, headers, session factory
│   ├── retry.py                   # RetryTransport with exponential backoff
│   ├── exceptions.py              # FidelityError hierarchy + DryRunError
│   ├── cli/                       # ft CLI tool (17 commands, typer + rich)
│   ├── auth/                      # 7-step login, TOTP 2FA, session keepalive, auto-refresh
│   ├── portfolio/                 # 8 modules
│   ├── orders/                    # 8 modules (equity, option, cancel, conditional, etc.)
│   ├── market_data/               # fastquote (chains + montage), chart
│   ├── research/                  # earnings, dividends, search, analytics, screener
│   ├── streaming/                 # MDDS WebSocket (quotes, L2, T&S) + news
│   ├── watchlists/, alerts/, settings/, reference/
│   └── models/                    # 25+ Pydantic v2 response models
│
├── service/                       # FastAPI REST service (thin wrapper around SDK)
│   ├── app.py                     # App factory, exception handlers, lifespan
│   ├── config.py                  # Settings with FTSERVICE_ env prefix
│   ├── session/                   # Session manager, credential store, keepalive
│   ├── streaming/                 # MDDS fan-out, SSE, WebSocket
│   └── routes/                    # 9 route files (57 endpoints)
│
├── docker/                        # Dockerfile, docker-compose, .env template
└── tests/                         # 1587 tests (respx for SDK, mock for service)
```

### Key Files
- **`client.py`** — Composes all 31 modules, `live_trading` flag, auto-refresh
- **`_http.py`** — Base URLs, ATP headers, `create_atp_session()`, `make_req_id()`
- **`auth/session.py`** — 7-step login handshake + TOTP 2FA (accepts 6-digit code or base32 secret)
- **`models/_parsers.py`** — Shared `_parse_float` / `_parse_int` helpers
- **`streaming/mdds.py`** — MDDS WebSocket client (quotes, Greeks, L2 virtualbook)
- **`cli/_app.py`** — Root typer app, registers all 17 commands
- **`cli/_session.py`** — Cookie persistence between CLI invocations
- **`service/app.py`** — FastAPI factory, SDK exception → HTTP error mapping

## Dry-Run Safety

**Orders default to preview-only.** Live trading requires explicit opt-in:
- SDK: `FidelityClient(live_trading=True)` or `FIDELITY_LIVE_TRADING=true` env var
- CLI: `--live` flag on buy/sell commands
- Service: `FTSERVICE_LIVE_TRADING=true` env var
- `DryRunError` raised when blocked — subclass of `FidelityError`
- Cancel is NEVER gated (always allowed)

## API Hosts

| Host | Base URL | Purpose |
|------|----------|---------|
| dpservice | `https://dpservice.fidelity.com` | Portfolio, orders, research, watchlists, preferences |
| fastquote | `https://fastquote.fidelity.com` | Option chains, montage/depth, charts (JSONP/XML) |
| ecaap | `https://ecaap.fidelity.com` | Authentication (7-step login + TOTP 2FA) |
| digital | `https://digital.fidelity.com` | Login page, security context, session management |
| ecawsgateway | `https://ecawsgateway.fidelity.com` | Alerts (SOAP/XML) |
| streaming-news | `https://streaming-news.mds.fidelity.com` | News streaming authorization |
| mdds | `wss://mdds-i-tc.fidelity.com` | Real-time market data WebSocket |
| livevol | `https://fidelity.apps.livevol.com` | Screener (SAML auth + ExecuteScan) |

## Headers

- **Login headers** (`REQUEST_HEADERS`): `AppId: RETAIL-CC-LOGIN-SDK`, `AppName: PILoginExperience`
- **Data/Trading headers** (`ATP_HEADERS`): `AppId: AP149323`, `AppName: Active Trader Desktop for Windows`
- Both include `User-Agent: ATPNext/4.4.1.7 FTPlusDesktop/4.4.1.7`
- Every request needs `fsreqid: REQ{uuid}`

## Authentication
- 7-step handshake against `ecaap.fidelity.com` (see `auth/session.py`)
- Cookies `ATC`, `FC`, `RC`, `SC` are the session tokens
- `ET` cookie is the auth token passed between login steps
- TOTP 2FA: accepts 6-digit code (passthrough) or base32 secret key (auto-generates via pyotp)
- Security context POST after login enables real-time quotes on fastquote
- Sessions expire ~30 min; use `session_keepalive.extend_session()` or `enable_auto_refresh()`

## API Quirks (from captures)
- Single-leg option place uses `previewInd: false, confInd: false` while equity uses `true/true`
- Single-leg options use endpoint `/v2`, multi-leg uses `/v1`
- Order modification is cancel-and-replace (atomic), not an edit — uses `orderNumOrig`
- Conditional orders use `parameters` (plural) top-level key, NOT `request.parameter`
- Conditional place: confNums applied to triggered legs only (index >= 1)
- Error responses return HTTP 200 with `respTypeCode: "E"` and `orderConfirmMsgs`
- L2 depth uses same MDDS WebSocket with `subscribe_virtualbook` command (25-level book, 200 field IDs)
- Fastquote endpoints return JSONP-wrapped XML
- Screener uses 3-step SAML auth: Fidelity → LiveVol JWT → ExecuteScan (XML response)
- Alerts use SOAP/XML on ecawsgateway with HTML-entity-encoded ALERT documents

## CLI Tool (`ft`)

Built on typer + rich. Session cookies persisted to `~/.config/ft/session.json` (Linux) or `%APPDATA%/ft/session.json` (Windows).

Commands: `login`, `logout`, `status`, `accounts`, `positions`, `balances`, `orders`, `buy`, `sell`, `cancel`, `quote`, `chart`, `search`, `earnings`, `dividends`, `stream`, `options` (subgroup: chain/buy/sell)

- `--format json` on any command for piped output
- `--live` + `--yes` on order commands for automated placement
- `--totp-token` for 6-digit code, `--totp-secret` for base32 key

## REST Service

FastAPI wrapper around all 31 SDK modules. All SDK calls use `asyncio.to_thread()`.

- Base URL: `http://localhost:8787/api/v1`
- Auth: API key via `Authorization: Bearer <key>` (optional, configurable)
- Response envelope: `{"ok": true, "data": {...}, "error": null}`
- Streaming: SSE at `/streaming/quotes`, WebSocket at `/ws/quotes`
- MDDS fan-out: one Fidelity connection, refcounted subscriptions, queue per consumer
- Config: `pydantic-settings` with `FTSERVICE_` env prefix

## Development

### Setup
```bash
pip install -e ".[dev,cli,service]"
```

### Testing
```bash
pytest                          # all 1587 tests
pytest tests/test_positions.py  # single module
pytest tests/test_cli*.py       # CLI tests only
pytest tests/test_service_*.py  # service tests only
ruff check src/ service/ tests/ # lint
```

### Code Conventions
- `httpx` for all HTTP (sync), `pydantic v2` for all response models
- `populate_by_name=True` and camelCase `Field(alias=...)` on all models
- `respx` for HTTP mocking in SDK tests, `unittest.mock` for service/CLI tests
- All modules receive the shared `httpx.Client` — never create their own
- `from_api_response()` class methods flatten Fidelity's nested JSON
- `_parse_float` / `_parse_int` from `models/_parsers.py` for numeric coercion
- Service tests use `httpx.AsyncClient` + `ASGITransport`, `app.dependency_overrides` for DI
- CLI tests use `typer.testing.CliRunner` + `strip_ansi()` helper (Rich outputs ANSI in non-TTY)
- Capture files (`*.flow`) and `data/` are gitignored

### Capture Workflow
All implementation comes from mitmproxy captures — never assume endpoint shapes.

1. Start proxy: `mitmweb --listen-port 8080 -w ~/capture.flow`
2. Install CA cert: `certutil -addstore Root "$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.cer"` (admin, one-time)
3. Enable system proxy: `reg add "HKCU\...\Internet Settings" /v ProxyEnable /t REG_DWORD /d 1 /f`
4. Use Trader+ and perform the target action
5. Disable proxy when done: set ProxyEnable back to 0
6. Analyze: `mitmdump -n -r ~/capture.flow -s ~/fidelity_filter.py`
7. Implement model + API module + client integration + tests from captured shapes

## Key Decisions

See `docs/DECISIONS.md` for all 22 locked product/technical decisions including:
- Package name: `fidelity-trader-api`, CLI: `ft`, mono-repo
- License: Apache 2.0
- Dry-run default, no order guardrails
- Credentials: env vars primary, AWS integrations, no local persistence
- SemVer versioning (pre-1.0: minor bumps may break)

## Module Reference

### Portfolio (8)
| Accessor | Endpoint |
|----------|----------|
| `positions` | `POST /ftgw/dp/position/v2` |
| `balances` | `POST /ftgw/dp/balance/detail/v2` |
| `accounts` | `POST /ftgw/dp/customer-am-acctnxt/v2/accounts` |
| `option_summary` | `POST /ftgw/dp/retail-am-optionsummary/v1` |
| `transactions` | `POST /ftgw/dp/accountmanagement/transaction/history/v2` |
| `closed_positions` | `POST /ftgw/dp/customer-am-position/v1/.../closedposition` |
| `loaned_securities` | `POST /ftgw/dp/retail-am-loanedsecurities/v1/.../rates` |
| `tax_lots` | `POST /ftgw/dp/orderentry/taxlot/v1` |

### Orders (8)
| Accessor | Endpoint |
|----------|----------|
| `equity_orders` | `POST /ftgw/dp/orderentry/equity/{preview,place}/v1` |
| `single_option_orders` | `POST /ftgw/dp/orderentry/option/{preview,place}/v2` |
| `option_orders` | `POST /ftgw/dp/orderentry/multilegoption/{preview,place}/v1` |
| `cancel_order` | `POST /ftgw/dp/orderentry/cancel/place/v1` |
| `cancel_replace` | `POST /ftgw/dp/orderentry/cancelandreplace/{preview,place}/v1` |
| `conditional_orders` | `POST /ftgw/dp/orderentry/conditional/{preview,place}/v1` |
| `staged_orders` | `POST /ftgw/dp/ent-research-staging/v1/.../staged-order/get` |
| `order_status` | `POST /ftgw/dp/retail-order-status/v3` |

### Market Data (2)
| Accessor | Endpoint |
|----------|----------|
| `option_chain` | `GET fastquote/service/quote/{chainLite,dtmontage}` |
| `chart` | `GET fastquote/service/marketdata/historical/chart/json` |

### Research (4)
| Accessor | Endpoint |
|----------|----------|
| `research` | `GET /ftgw/dpdirect/research/{earning,dividend}/v1` |
| `search` | `GET /ftgw/dpdirect/search/autosuggest/v1` |
| `option_analytics` | `POST /ftgw/dp/research/option/positions/analytics/v1` |
| `screener` | `POST fidelity.apps.livevol.com ExecuteScan` (SAML auth) |

### Streaming (3)
| Accessor | Protocol |
|----------|----------|
| MDDS quotes | `subscribe` on `wss://mdds-i-tc.fidelity.com` |
| MDDS L2 book | `subscribe_virtualbook` on same WebSocket (25-level, 200 fields) |
| `streaming` | `POST streaming-news/ftgw/snaz/Authorize` |

### Other (6)
| Accessor | Endpoint |
|----------|----------|
| `watchlists` | `POST /ftgw/dp/retail-watchlist/v1/.../get` |
| `alerts` | `POST ecawsgateway/ftgw/alerts/services/ATBTSubscription` |
| `price_triggers` | `GET+POST /ftgw/dp/retail-price-triggers/v1` |
| `preferences` | `POST /ftgw/dp/.../atn-prefs/{get,save,delete}preference` |
| `available_markets` | `POST /ftgw/dp/reference/security/stock/availablemarket/v1` |
| `holiday_calendar` | `GET /ftgw/dpdirect/market/holidaycalendar/v1` |
| `security_context` | `POST digital/ftgw/digital/pico/api/v1/context/security` |
| `session_keepalive` | `GET digital/ftgw/digital/portfolio/extendsession` |
