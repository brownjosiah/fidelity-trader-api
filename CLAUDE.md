# Fidelity Trader SDK

## Project Overview
Unofficial Python SDK that replicates the Fidelity Trader+ desktop application's API calls. Built entirely by reverse-engineering network traffic via mitmproxy captures — no assumptions, no other repos.

**25 API modules, 994 tests, Python 3.10+**

## Architecture

All modules share a single `httpx.Client` instance via `FidelityClient`, so cookies (the auth mechanism) propagate automatically.

```
FidelityClient (client.py)
├── _http: httpx.Client              ← shared cookie jar
├── _auth: AuthSession               ← 7-step login + CSRF
├── 8 portfolio modules               (positions, balances, accounts, ...)
├── 5 order modules                   (equity, single option, multi-leg, cancel, cancel-replace)
├── 2 market data modules             (fastquote, chart)
├── 3 research modules                (earnings/dividends, search, analytics)
├── 3 streaming modules               (MDDS quotes + L2, news auth)
├── watchlists, alerts, preferences, available_markets, security_context
└── close()
```

### Key Files
- **`client.py`** — Composes all 25 modules
- **`_http.py`** — Base URLs, headers, session factory
- **`auth/session.py`** — 7-step login handshake + TOTP 2FA
- **`models/_parsers.py`** — Shared `_parse_float` / `_parse_int` helpers
- **`streaming/mdds.py`** — MDDS WebSocket client (quotes, options with Greeks, L2 virtualbook)
- **`streaming/mdds_fields.py`** — Field ID mappings (equity, option, T&S, L2)

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

## Headers

Two header sets depending on the API:

- **Login headers** (`REQUEST_HEADERS`): `AppId: RETAIL-CC-LOGIN-SDK`, `AppName: PILoginExperience`
- **Data/Trading headers** (`ATP_HEADERS`): `AppId: AP149323`, `AppName: Active Trader Desktop for Windows`
- Both include `User-Agent: ATPNext/4.4.1.7 FTPlusDesktop/4.4.1.7`
- Every request needs `fsreqid: REQ{uuid}`

## Authentication
- 7-step handshake against `ecaap.fidelity.com` (see `auth/session.py`)
- Cookies `ATC`, `FC`, `RC`, `SC` are the session tokens
- `ET` cookie is the auth token passed between login steps
- TOTP 2FA handled automatically when `totp_secret` is provided
- Security context POST after login enables real-time quotes on fastquote

## API Quirks (from captures)
- Single-leg option place uses `previewInd: false, confInd: false` while equity uses `true/true`
- Single-leg options use endpoint `/v2`, multi-leg uses `/v1`
- Order modification is cancel-and-replace (atomic), not an edit — uses `orderNumOrig`
- Error responses return HTTP 200 with `respTypeCode: "E"` and `orderConfirmMsgs`
- L2 depth uses same MDDS WebSocket with `subscribe_virtualbook` command (25-level book)
- Fastquote endpoints return JSONP-wrapped XML

## Development

### Setup
```bash
pip install -e ".[dev]"
```

### Testing
```bash
pytest                          # all 994 tests
pytest tests/test_positions.py  # single module
pytest --cov=fidelity_trader    # with coverage
```

### Code Conventions
- `httpx` for all HTTP (sync), `pydantic v2` for all response models
- `populate_by_name=True` and camelCase aliases on all models
- `respx` for HTTP mocking in tests
- All modules receive the shared `httpx.Client` — never create their own
- `from_api_response()` class methods flatten Fidelity's nested JSON
- `_parse_float` / `_parse_int` from `models/_parsers.py` for numeric coercion
- Capture files (`*.flow`) are gitignored

### Capture Workflow
All implementation comes from mitmproxy captures — never assume endpoint shapes.

1. Start proxy: `mitmweb --listen-port 8080 -w ~/capture.flow`
2. Install CA cert: `certutil -addstore Root "$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.cer"` (admin, one-time)
3. Enable system proxy: `reg add "HKCU\...\Internet Settings" /v ProxyEnable /t REG_DWORD /d 1 /f`
4. Use Trader+ and perform the target action
5. Disable proxy when done: set ProxyEnable back to 0
6. Extract data: `python -c "from mitmproxy.io import FlowReader; ..."`
7. Implement model + API module + tests from the captured shapes

### Filter Scripts
- `~/fidelity_filter.py` — ecaap + /prgw/ endpoints
- `~/fidelity_portfolio_filter.py` — dpservice + streaming-news
- `~/fastquote_filter.py` — fastquote + ecawsgateway + accounts + analytics
- `~/ws_dump.py` / `~/ws_dump_full.py` — WebSocket message extractors

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

### Orders (5)
| Accessor | Endpoint |
|----------|----------|
| `equity_orders` | `POST /ftgw/dp/orderentry/equity/{preview,place}/v1` |
| `single_option_orders` | `POST /ftgw/dp/orderentry/option/{preview,place}/v2` |
| `option_orders` | `POST /ftgw/dp/orderentry/multilegoption/{preview,place}/v1` |
| `cancel_order` | `POST /ftgw/dp/orderentry/cancel/place/v1` |
| `cancel_replace` | `POST /ftgw/dp/orderentry/cancelandreplace/{preview,place}/v1` |

### Market Data (2)
| Accessor | Endpoint |
|----------|----------|
| `option_chain` | `GET fastquote/service/quote/{chainLite,dtmontage}` |
| `chart` | `GET fastquote/service/marketdata/historical/chart/json` |

### Research (3)
| Accessor | Endpoint |
|----------|----------|
| `research` | `GET /ftgw/dpdirect/research/{earning,dividend}/v1` |
| `search` | `GET /ftgw/dpdirect/search/autosuggest/v1` |
| `option_analytics` | `POST /ftgw/dp/research/option/positions/analytics/v1` |

### Streaming (3)
| Accessor | Protocol |
|----------|----------|
| MDDS quotes | `subscribe` on `wss://mdds-i-tc.fidelity.com` |
| MDDS L2 book | `subscribe_virtualbook` on same WebSocket |
| `streaming` | `POST streaming-news/ftgw/snaz/Authorize` |

### Other (4)
| Accessor | Endpoint |
|----------|----------|
| `watchlists` | `POST /ftgw/dp/retail-watchlist/v1/.../get` |
| `alerts` | `POST ecawsgateway/ftgw/alerts/services/ATBTSubscription` |
| `preferences` | `POST /ftgw/dp/.../atn-prefs/{get,save,delete}preference` |
| `available_markets` | `POST /ftgw/dp/reference/security/stock/availablemarket/v1` |
| `security_context` | `POST digital/ftgw/digital/pico/api/v1/context/security` |
