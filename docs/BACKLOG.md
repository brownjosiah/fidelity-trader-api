# Fidelity Trader SDK — Project Backlog

> Last updated: 2026-04-03
> Current state: **31 SDK modules**, **17 CLI commands**, **57 service endpoints**, **1587 tests**, **8 capture files**

---

## Implemented Modules (31)

| # | Accessor | Class | Endpoint | Host |
|---|----------|-------|----------|------|
| 1 | `positions` | PositionsAPI | `POST /ftgw/dp/position/v2` | dpservice |
| 2 | `balances` | BalancesAPI | `POST /ftgw/dp/balance/detail/v2` | dpservice |
| 3 | `option_summary` | OptionSummaryAPI | `POST /ftgw/dp/retail-am-optionsummary/v1/.../get` | dpservice |
| 4 | `transactions` | TransactionsAPI | `POST /ftgw/dp/accountmanagement/transaction/history/v2` | dpservice |
| 5 | `order_status` | OrderStatusAPI | `POST /ftgw/dp/retail-order-status/v3/.../status-summary` | dpservice |
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
| 24 | `single_option_orders` | SingleOptionOrderAPI | `POST /ftgw/dp/orderentry/option/{preview,place}/v2` | dpservice |
| 25 | `cancel_replace` | CancelReplaceAPI | `POST /ftgw/dp/orderentry/cancelandreplace/{preview,place}/v1` | dpservice |
| 26 | `conditional_orders` | ConditionalOrderAPI | `POST /ftgw/dp/orderentry/conditional/{preview,place}/v1` | dpservice |
| 27 | `staged_orders` | StagedOrderAPI | `POST /ftgw/dp/ent-research-staging/v1/.../staged-order/get` | dpservice |
| 28 | `session_keepalive` | SessionKeepAliveAPI | `GET /ftgw/digital/portfolio/extendsession` | digital |
| 29 | `holiday_calendar` | HolidayCalendarAPI | `GET /ftgw/dpdirect/market/holidaycalendar/v1` | dpservice |
| 30 | `price_triggers` | PriceTriggersAPI | `GET+POST /ftgw/dp/retail-price-triggers/v1/.../list,create,delete` | dpservice |
| 31 | `screener` | ScreenerAPI | `POST fidelity.apps.livevol.com ExecuteScan via SAML` | livevol |

**Streaming (non-REST):**
- MDDS WebSocket (`wss://mdds-i-tc.fidelity.com/?productid=atn`) — live quotes, options w/ Greeks, T&S fields (1159-1165)
- MDDS L2 virtualbook (`subscribe_virtualbook` on same WebSocket) — 25-level order book depth

**Hosts:**
- `dpservice.fidelity.com` — Portfolio, orders, research, watchlists, preferences
- `fastquote.fidelity.com` — Option chains, montage, charts (JSONP)
- `ecaap.fidelity.com` — Authentication (7-step login + TOTP 2FA)
- `digital.fidelity.com` — Login page, security context, session management
- `ecawsgateway.fidelity.com` — Alerts (SOAP/XML)
- `streaming-news.mds.fidelity.com` — News streaming auth
- `mdds-i-tc.fidelity.com` — Real-time market data WebSocket
- `fidelity.apps.livevol.com` — Screener (LiveVol ExecuteScan via SAML)
- `fidelity-widgets.financial.com` — SAML auth for screener

---

## Backlog

### 1. Captured but Not Implemented

Endpoints that exist in our mitmproxy capture files but have no SDK module.

| # | Endpoint | Source | Priority | Status | Notes |
|---|----------|--------|----------|--------|-------|
| 1.1 | `GET .../dpdirect/market/holidaycalendar/v1` | websocket capture | Medium | DONE | Market holiday schedule with full/abbreviated day support |
| 1.2 | `POST .../ent-research-staging/v1/customers/staged-order/get` | websocket capture | Medium | DONE | Staged/saved orders retrieval |
| 1.3 | `POST .../research/tool/notebook/note/detail/v1` | portfolio capture | Low | TODO | Notes/notebook feature (capture returned "no notes" — needs data to model) |
| 1.4 | `GET .../retail-price-triggers/v1/.../alert/price-triggers/list` | websocket capture | Medium | DONE | Price alert triggers list with pagination |
| 1.5 | `POST .../retail-indepInvs-pref/v1/getPreference` | websocket capture | Low | TODO | Shared chart preferences (separate pref system from ATN prefs) |
| 1.6 | `GET .../content-headless/v2/content` | portfolio capture | Low | TODO | App announcements/content CMS — minimal user value |
| 1.7 | `GET .../ftgw/digital/portfolio/extendsession` | capture | Medium | DONE | Session keep-alive with is_session_alive convenience method |
| 1.8 | `POST .../prgw/digital/login/logging/new-entry` | capture | Skip | — | Internal telemetry/logging — no user value |

### 2. Needs New Captures

Features that exist in Trader+ but we haven't captured the traffic yet.

| # | Feature | Expected Endpoint | Priority | Status | Notes |
|---|---------|-------------------|----------|--------|-------|
| 2.1 | **Single-leg option orders** | `orderentry/option/preview+place/v2` | **High** | DONE | SingleOptionOrderAPI with preview/place, previewInd=false quirk |
| 2.2 | **Order modification** | `orderentry/cancelandreplace/preview+place/v1` | **High** | DONE | CancelReplaceAPI — atomic cancel-and-replace using orderNumOrig |
| 2.3 | **Conditional/triggered orders** | `orderentry/conditional/preview+place/v1` | **High** | DONE | OTOCO/OTO/OCO with stop + limit legs — captured 2026-04-02 |
| 2.4 | **Watchlist CRUD** | `retail-watchlist/v1/.../save` | Medium | PARTIAL | save_watchlist() added — create/delete still TODO |
| 2.5 | **Alerts CRUD** | Likely same ecawsgateway SOAP | Medium | TODO | Create/edit/delete alerts (we only have subscribe) |
| 2.6 | **Full priced option chain** | Different fastquote endpoint or params | Medium | TODO | Live bid/ask for all strikes (chainLite is summary only) |
| 2.7 | **Margin details** | `balance/detail/v2` (enhanced models) | Medium | DONE | MarginDetail, OptionsDetail, ShortDetail, BondDetail, SimplifiedMarginDetail added to existing BalancesAPI |
| 2.8 | **Stock/option screener** | LiveVol `ExecuteScan` via SAML auth | Medium | DONE | 3-step SAML auth + XML scan results from fidelity.apps.livevol.com |
| 2.9 | **News feed WebSocket** | `fid-str.newsedge.net:443` | Medium | TODO | We have auth token but not the actual news stream protocol |
| 2.10 | **Fundamentals/company data** | Unknown (dpservice or fastquote) | Medium | TODO | Revenue, EPS, P/E, sector, company profile data |
| 2.11 | **Analyst ratings** | Unknown | Low | TODO | Buy/sell/hold consensus ratings |
| 2.12 | **Account transfers** | Unknown | Low | TODO | Move funds between accounts |
| 2.13 | **Document downloads** | Unknown | Low | TODO | Statements, tax docs, trade confirms |
| 2.14 | **DRIP settings** | Unknown | Low | TODO | Dividend reinvestment plan configuration |

### 3. Streaming / WebSocket Gaps

| # | Feature | Current State | Priority | Status | Notes |
|---|---------|---------------|----------|--------|-------|
| 3.1 | **L2 streaming depth** | Snapshot + streaming virtualbook | **High** | DONE | 25-level order book via `subscribe_virtualbook` on MDDS WebSocket — captured in ts_l2_capture.flow |
| 3.2 | **News WebSocket feed** | Auth captured, feed NOT | Medium | TODO | Have the authorize call, need the newsedge.net WebSocket protocol |
| 3.3 | **MDDS reconnection/heartbeat** | Not implemented | Low | TODO | Auto-reconnect on disconnect, heartbeat keep-alive for production use |

### 4. SDK Infrastructure / Quality

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 4.1 | **Clean up stale models/account.py** | Medium | DONE | Extracted _parse_float/_parse_int to _parsers.py, removed stale classes |
| 4.2 | **Update CLAUDE.md** | Medium | DONE | Rewritten for 31 modules, CLI, service, dry-run, 1587 tests |
| 4.3 | **Update full_walkthrough.py** | Medium | DONE | Updated to cover all 31 modules |
| 4.4 | **Session keep-alive / auto-refresh** | Medium | DONE | `SessionAutoRefresh` daemon thread + `SessionKeepAliveAPI.extend_session()` |
| 4.5 | **Async client option** | Low | DONE | `AsyncFidelityClient` via `asyncio.to_thread`, 17 tests |
| 4.6 | **Rate limiting / retry logic** | Low | DONE | `RetryTransport` with exponential backoff, 429/5xx retry, 32 tests |
| 4.7 | **PyPI packaging / CI** | Low | DONE | GitHub Actions for pytest + ruff CI and PyPI trusted publishing |

### 5. Product & Release (from [DECISIONS.md](DECISIONS.md))

| # | Item | Priority | Status | Notes |
|---|------|----------|--------|-------|
| 5.1 | **CLI tool (`ft` command)** | **High** | DONE | 17 commands, typer + rich, session persistence, dry-run UX |
| 5.2 | **Dry-run mode** | **High** | DONE | SDK DryRunError + CLI `--live` flag + service FTSERVICE_LIVE_TRADING |
| 5.3 | **License update to Apache 2.0** | **High** | DONE | pyproject.toml + LICENSE file updated |
| 5.4 | **Package rename to `fidelity-trader-api`** | **High** | DONE | pyproject.toml updated, import name unchanged (`fidelity_trader`) |
| 5.5 | **Service layer (FastAPI)** | **High** | DONE | 57 endpoints, streaming fan-out, Docker packaging |
| 5.6 | **GitHub Pages docs site** | Medium | TODO | MkDocs Material, deployed via GitHub Actions |
| 5.7 | **CI smoke tests (real account)** | Medium | TODO | Real Fidelity account, secrets in GitHub Actions |
| 5.8 | **Docker Hub publishing** | Medium | TODO | Publish to GHCR + Docker Hub on release (workflow exists, needs secrets) |
| 5.9 | **HashiCorp Vault credential provider** | Low | TODO | Complement existing AWS SM/SSM providers |
| 5.10 | **Azure Key Vault credential provider** | Low | TODO | |
| 5.11 | **Official TypeScript client** | Low | TODO | Generated from OpenAPI spec. Depends on 5.15 |
| 5.12 | **Official Go client** | Low | TODO | Generated from OpenAPI spec. Depends on 5.15 |
| 5.13 | **Contribution guide** | Low | TODO | Capture-driven contribution model, how to capture + implement |
| 5.14 | **Webhook/callback system** | Low | TODO | Phase 3 — POST to URL on order fill, price trigger |
| 5.15 | **OpenAPI response typing** | Medium | TODO | See details below |
| 5.16 | **OpenAPI spec export + Makefile** | Low | TODO | `make openapi` + `make clients`. Depends on 5.15 |
| 5.17 | **Publish openapi.json as release artifact** | Low | TODO | Attach to GitHub Release. Depends on 5.16 |
| 5.18 | **CI schema regression check** | Low | TODO | Fail if any response schema is empty. Depends on 5.15 |

### 5.15 Detail: OpenAPI Response Typing

**Problem:** All 52 response schemas in the auto-generated OpenAPI spec are empty (`{}`). Client generators produce `any`/`interface{}` for every response — useless.

**Root cause:** Routes return plain `dict` from `success()`. FastAPI can't infer response types.

**Solution:** Refactor `APIResponse` to `Generic[T]`, add `response_model=APIResponse[SdkModel]` to every route decorator.

**Scope:**
- Refactor `service/models/responses.py` — make `APIResponse` generic (`data: Optional[T]`)
- Create 5 Pydantic mirror models for dataclass SDK types (OptionChain, Montage, Chart, ScanResult, AlertActivation)
- Create 11 small Pydantic schemas for inline dict responses (AuthStatus, HealthCheck, ServiceInfo, etc.)
- Add `response_model=` parameter to all 51 route decorators across 10 route files
- Add test verifying no empty schemas in `/openapi.json`
- ~400 lines of changes, ~8-10 hours estimated

**Dependency chain:** 5.15 → 5.16 (export script) → 5.17 (release artifact) + 5.18 (CI check) → 5.11/5.12 (TS/Go clients)

---

## Priority Summary

MVP complete (SDK + CLI + Service). Remaining work is ecosystem, polish, and capture-dependent features. See [PRODUCT_VISION.md](PRODUCT_VISION.md) for strategy and [DECISIONS.md](DECISIONS.md) for locked decisions.

| Priority | Done | Remaining | Items |
|----------|------|-----------|-------|
| **High** | 9 | 0 | All done: ~~Single-leg options (2.1)~~, ~~Order modify (2.2)~~, ~~Conditional orders (2.3)~~, ~~L2 streaming (3.1)~~, ~~License (5.3)~~, ~~Package rename (5.4)~~, ~~CLI tool (5.1)~~, ~~Dry-run mode (5.2)~~, ~~Service layer (5.5)~~ |
| **Medium** | 13 | 8 | Done: ~~Holiday calendar (1.1)~~, ~~Staged orders (1.2)~~, ~~Price triggers (1.4)~~, ~~Session keepalive (1.7)~~, ~~Margin (2.7)~~, ~~Screener (2.8)~~, ~~Stale models (4.1)~~, ~~CLAUDE.md (4.2)~~, ~~Walkthrough (4.3)~~, ~~Session refresh (4.4)~~. Remaining: Watchlist CRUD (2.4), Alerts CRUD (2.5), Full option chain (2.6), News feed (2.9/3.2), Fundamentals (2.10), Docs site (5.6), CI smoke tests (5.7), Docker Hub (5.8), OpenAPI response typing (5.15) |
| **Low** | 3 | 18 | Done: ~~Async (4.5)~~, ~~Retry (4.6)~~, ~~PyPI/CI (4.7)~~. Remaining: Notebook (1.3), Shared prefs (1.5), Content CMS (1.6), Analyst ratings (2.11), Transfers (2.12), Docs (2.13), DRIP (2.14), MDDS reconnect (3.3), Vault (5.9), Azure KV (5.10), TS client (5.11), Go client (5.12), Contribution guide (5.13), Webhooks (5.14), OpenAPI export (5.16), Spec release artifact (5.17), CI schema check (5.18) |
| **Skip** | 1 | 0 | Login logging/telemetry (1.8) |

---

## Capture Files

| File | Contents |
|------|----------|
| `~/fidelity_capture.flow` | Initial login, positions, balances, accounts, preferences |
| `~/fidelity_portfolio_capture.flow` | Transactions, option summary, closed positions, loaned securities, watchlists |
| `~/fidelity_market_hours_capture.flow` | Orders (equity/option/cancel), tax lots, available markets, analytics, chart, montage |
| `~/fidelity_2fa_capture.flow` | TOTP 2FA flow, option chain, alerts, search, news auth |
| `~/fidelity_websocket_capture.flow` | MDDS WebSocket, holiday calendar, price triggers, staged orders |
| `~/fidelity_ts_l2_capture.flow` | Time & Sales / L2 capture attempt (limited — native app bypassed proxy) |
| `~/fidelity_trading_capture.flow` | Single-leg options, cancel-replace, session keepalive |
| `~/fidelity_crud_capture.flow` | Conditional orders, watchlist save, price triggers CRUD, screener, alerts, margin details |

## Filter Scripts

| Script | Filters |
|--------|---------|
| `~/fidelity_filter.py` | ecaap + /prgw/ endpoints |
| `~/fidelity_portfolio_filter.py` | dpservice + streaming-news |
| `~/fastquote_filter.py` | fastquote + ecawsgateway + accounts + analytics + pico |
| `~/ws_dump.py` | WebSocket message extractor |
| `~/ws_dump_full.py` | Full WebSocket message dump |
| `~/extract_fields.py` | MDDS field ID extractor |
