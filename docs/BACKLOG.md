# Fidelity Trader SDK — Project Backlog

> Last updated: 2026-03-31
> Current state: **23 API modules**, **822 tests**, **6 capture files**

---

## Implemented Modules (23)

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

**Streaming (non-REST):**
- MDDS WebSocket (`wss://mdds-i-tc.fidelity.com/?productid=atn`) — live quotes, options w/ Greeks, T&S fields (1159-1165)

**Hosts:**
- `dpservice.fidelity.com` — Portfolio, orders, research, watchlists, preferences
- `fastquote.fidelity.com` — Option chains, montage, charts (JSONP)
- `ecaap.fidelity.com` — Authentication (7-step login + TOTP 2FA)
- `digital.fidelity.com` — Login page, security context, session management
- `ecawsgateway.fidelity.com` — Alerts (SOAP/XML)
- `streaming-news.mds.fidelity.com` — News streaming auth
- `mdds-i-tc.fidelity.com` — Real-time market data WebSocket

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
| 2.1 | **Single-leg option orders** | `orderentry/option/preview+place/v2` | **High** | CAPTURED | Captured 2026-04-02 in `fidelity_trading_capture.flow` — ready to implement |
| 2.2 | **Order modification** | `orderentry/cancelandreplace/preview+place/v1` | **High** | CAPTURED | Cancel-and-replace workflow captured 2026-04-02 — ready to implement |
| 2.3 | **Conditional/triggered orders** | `orderentry/conditional/preview+place/v1` | **High** | DONE | OTOCO/OTO/OCO with stop + limit legs — captured 2026-04-02 |
| 2.4 | **Watchlist CRUD** | `retail-watchlist/v1/.../save` | Medium | PARTIAL | save_watchlist() added — create/delete still TODO |
| 2.5 | **Alerts CRUD** | Likely same ecawsgateway SOAP | Medium | TODO | Create/edit/delete alerts (we only have subscribe) |
| 2.6 | **Full priced option chain** | Different fastquote endpoint or params | Medium | TODO | Live bid/ask for all strikes (chainLite is summary only) |
| 2.7 | **Margin details** | Unknown | Medium | TODO | Margin requirements, buying power breakdown |
| 2.8 | **Stock/option screener** | Unknown | Medium | TODO | Scanner/screener functionality from Trader+ |
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
| 4.1 | **Clean up stale models/account.py** | Medium | DONE | Extracted _parse_float/_parse_int to _parsers.py, removed stale Account/Balance/Position classes |
| 4.2 | **Update CLAUDE.md** | Medium | DONE | Rewritten to reflect 25-module architecture, all hosts, API quirks, capture workflow |
| 4.3 | **Update full_walkthrough.py** | Medium | TODO | Example should cover all 23 modules including new ones |
| 4.4 | **Session keep-alive / auto-refresh** | Medium | TODO | No automatic session extension — long-running apps will timeout |
| 4.5 | **Async client option** | Low | TODO | All modules are sync httpx; could add async variants |
| 4.6 | **Rate limiting / retry logic** | Low | TODO | No retry on transient failures |
| 4.7 | **PyPI packaging / CI** | Low | TODO | pyproject.toml exists but no publish workflow or CI pipeline |

---

## Priority Summary

All SDK work (Phases 1-4 below) takes priority over the service layer. The self-hosted REST/WebSocket service ([`SERVICE_PLAN.md`](SERVICE_PLAN.md)) is Phase 2 of the overall project roadmap and should begin once the core trading workflow is complete.

| Priority | Count | Items |
|----------|-------|-------|
| **High** | 4 | Single-leg options (2.1), Order modify (2.2), Conditional orders (2.3), L2 streaming (3.1) |
| **Medium** | 17 | Holiday calendar (1.1), Staged orders (1.2), Price triggers (1.4), Session keepalive (1.7), Watchlist CRUD (2.4), Alerts CRUD (2.5), Full option chain (2.6), Margin (2.7), Screener (2.8), News feed (2.9/3.2), Fundamentals (2.10), Stale models (4.1), CLAUDE.md (4.2), Walkthrough (4.3), Session refresh (4.4) |
| **Low** | 10 | Notebook (1.3), Shared prefs (1.5), Content CMS (1.6), Analyst ratings (2.11), Transfers (2.12), Docs (2.13), DRIP (2.14), MDDS reconnect (3.3), Async (4.5), Retry (4.6), PyPI (4.7) |
| **Skip** | 1 | Login logging/telemetry (1.8) |

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

## Filter Scripts

| Script | Filters |
|--------|---------|
| `~/fidelity_filter.py` | ecaap + /prgw/ endpoints |
| `~/fidelity_portfolio_filter.py` | dpservice + streaming-news |
| `~/fastquote_filter.py` | fastquote + ecawsgateway + accounts + analytics + pico |
| `~/ws_dump.py` | WebSocket message extractor |
| `~/ws_dump_full.py` | Full WebSocket message dump |
| `~/extract_fields.py` | MDDS field ID extractor |
