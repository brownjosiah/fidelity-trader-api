# Fidelity Trader+ v4.5.1.4 — Decompilation Reference

> **Date:** 2026-04-04
> **Method:** ILSpy decompilation of all first-party .NET assemblies
> **Source:** 97 projects, 8,784 C# files, ~893,000 lines of code
> **Status:** Complete — all 7 analysis phases finished

This document is the single authoritative reference for everything discovered by reverse-engineering the Fidelity Trader+ desktop application via .NET decompilation. It consolidates findings from all analysis files in `~/fidelity-decomp/analysis/`.

---

## Table of Contents

1. [Application Architecture](#1-application-architecture)
2. [Complete API Surface](#2-complete-api-surface)
3. [MDDS Streaming Protocol](#3-mdds-streaming-protocol)
4. [BEPS GraphQL Event Streaming](#4-beps-graphql-event-streaming)
5. [Data Models & Enums](#5-data-models--enums)
6. [Configuration Schemas](#6-configuration-schemas)
7. [Feature Flags](#7-feature-flags)
8. [SDK Gap Analysis](#8-sdk-gap-analysis)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [File Locations](#10-file-locations)

---

## 1. Application Architecture

### Tech Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| **Runtime** | .NET 10.0.3 | Self-contained, x64, Workstation GC |
| **UI Framework** | .NET MAUI + WinUI 3 | WindowsAppSDK 1.7, Telerik Maui Controls |
| **State Management** | Fluxor 5.6.1-fmr.20251205 | Custom FMR fork, Redux pattern (Action → Reducer → State, Effect → API) |
| **MVVM** | CommunityToolkit.Mvvm | `[ObservableProperty]`, `[RelayCommand]` |
| **HTTP Client** | Refit + Polly | Declarative typed REST interfaces with resilience policies |
| **Rendering** | SkiaSharp + Win2D + WPF interop | Charts via WebView2 (Edge/Chromium) |
| **Streaming** | Custom `Fmr.SocketClient` (WebSocket) | MDDS/QWS protocol for real-time market data |
| **Messaging** | TIBCO.EMS (legacy) → BEPS/GraphQL (new) | AWS AppSync GraphQL for alert events |
| **Logging** | Serilog (file + console + debug) | OpenTelemetry OTLP exporter for telemetry |
| **Feature Flags** | LaunchDarkly | 48 flags prefixed `ATN-` |
| **Crypto** | Chaos.NaCl (libsodium) | NaCl encryption |
| **Distribution** | MSIX via Microsoft Store | `runFullTrust` capability, signed by FMR LLC |

### Internal Codenames

| Name | What It Is |
|------|-----------|
| **Sirius** | Platform core framework (`Fmr.Sirius.dll`) |
| **SuperNova** | Application shell (`Fmr.SuperNova.Core.dll`, `Fmr.SuperNova.Desktop.dll`) |
| **Nebula** | Data/service layer (`Fmr.Nebula.dll` — 672 files, 2MB) |
| **NovaUI** | UI component framework (`Fmr.NovaUI.dll` — 661 files, 6.4MB) |
| **iveTrader** | Internal project name (found in Jenkins build paths) |
| **ATP / ATPNext** | Active Trader Pro / Next-gen rebrand |

### Assembly Inventory

**97 decompiled assemblies** — 62 core + 35 UI counterparts:

| Category | Count | Key Assemblies |
|----------|-------|----------------|
| API/Network | 4 | `Fmr.ApiHeader`, `Fmr.SocketClient`, `Fmr.WebLogin`, `Fmr.BepsAlertStreaming` |
| Business Domain | 48 | `Fmr.Orders` (315 files), `Fmr.Trade` (482 files), `Fmr.Positions` (259 files), `Fmr.Quote` (230 files), etc. |
| Platform Core | 8 | `Fmr.Sirius` (285 files), `Fmr.SuperNova.Desktop` (426 files), `Fmr.Nebula` (672 files), `Fmr.NovaUI` (661 files) |
| App Entry | 1 | `Fidelity Trader+.dll` (DI registration, startup) |
| Utilities | 36 | Config, DateTime, Themes, HotKeys, Keyboard, Magnetize, etc. |

### Base URL Domains (10)

| Domain | Purpose | SDK Constant |
|--------|---------|-------------|
| `dpservice.fidelity.com` | Primary REST gateway (portfolio, orders, research, watchlists, preferences) | `DPSERVICE_URL` |
| `fastquote.fidelity.com` | Market data (option chains, montage, charts, T&S) | `FASTQUOTE_URL` |
| `ecaap.fidelity.com` | Authentication (7-step login + TOTP 2FA) | `AUTH_URL` |
| `digital.fidelity.com` | Login page, security context, session keepalive, RTM | `BASE_URL` |
| `ecawsgateway.fidelity.com` | Alerts (SOAP/XML, legacy + historical) | `ALERTS_URL` |
| `streaming-news.mds.fidelity.com` | News streaming authorization | `STREAMING_NEWS_URL` |
| `mdds-i-tc.fidelity.com` | Real-time market data WebSocket | (in `mdds.py`) |
| `spservice.fidelity.com` | BEPS alert streaming (AppSync GraphQL WebSocket) | **NEW — not in SDK** |
| `contentapi.fidelity.com` | Headless CMS content/notifications | **NEW — not in SDK** |
| `dpservicexq1.fidelity.com` | Cash accruals (UAT/XQ1 variant of dpservice) | **NEW — not in SDK** |

---

## 2. Complete API Surface

**88 total endpoints:** 77 REST (via 35 Refit interfaces) + 5 WebSocket + 2 SOAP + 4 direct HttpClient

### Header Construction

All headers are built by `Fmr.ApiHeader.dll` using a **FilterChain** pattern — each endpoint category gets a specific chain of header resolvers:

| Header | Value | Notes |
|--------|-------|-------|
| `AppId` | `AP149323` (data) / `RETAIL-CC-LOGIN-SDK` (auth) | Varies by endpoint |
| `AppName` | `Active Trader Desktop for Windows` (data) / `PILoginExperience` (auth) | Varies by endpoint |
| `User-Agent` | `ATPNext/4.5.1.4 FTPlusDesktop/4.5.1.4` | SDK currently sends `4.4.1.7` — outdated |
| `fsreqid` | `REQ{guid-no-dashes}` | Unique per request |
| `CL` | `3` | On order status, loaned securities, hard-to-borrow |
| `Accept-Token-Type` | `ET` | On auth endpoints |
| `fid-originating-app-id` | varies | On accruals, short insights |
| `FID-LOG-TRACKING-ID` | `REQ{guid}` | On staged orders |
| `WhereUsed` | `ActiveTraderMessageCenter` | On headless CMS |
| `SOAPAction` | `CustomerSignOn` | On legacy alert SOAP |

### REST Endpoints by Domain

#### Accounts (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/customer-am-acctnxt/v2/accounts` | `ILwcAccount` | Implemented (`accounts`) |
| POST | `/customer-am-feature/v2/accounts/features/get` | `ILwcAccount` | **MISSING** — account capabilities, margin level, options approval |

#### Positions (3 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/position/v2` | `ILwcPositions` | Implemented (`positions`) |
| POST | `/position/open/lots/v1` | `ILwcPositions` | **MISSING** — tax lot detail per position |
| POST | `/retail-am-hardtoborrow/v1/.../rates/borrow` | `ILwcHardToBorrow` | **MISSING** — HTB rates for positions |

#### Balances (1 endpoint)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/balance/detail/v2` | `ILwcBalances` | Implemented (`balances`) |

#### Order Status (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/retail-order-status/v3/.../status-summary` | `ILwcOrders` | Implemented (`order_status`) |
| POST | `/retail-order-status/v3/.../status-detail` | `ILwcOrders` | **MISSING** — single order detail |

#### Equity Orders (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/orderentry/equity/preview/v1` | `ILwcEquityOrder` | Implemented (`equity_orders`) |
| POST | `/orderentry/equity/place/v1` | `ILwcEquityOrder` | Implemented (`equity_orders`) |

#### Single-Leg Option Orders (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/orderentry/option/preview/v2` | `ILwcSloOrder` | Implemented (`single_option_orders`) |
| POST | `/orderentry/option/place/v2` | `ILwcSloOrder` | Implemented (`single_option_orders`) |

#### Multi-Leg Option Orders (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/orderentry/multilegoption/preview/v1` | `ILwcMloOrder` | Implemented (`option_orders`) |
| POST | `/orderentry/multilegoption/place/v1` | `ILwcMloOrder` | Implemented (`option_orders`) |

#### Cancel Orders (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/orderentry/cancel/preview/v1` | `ILwcCancelOrder` | **MISSING** — preview with warnings, proceeds, commission |
| POST | `/orderentry/cancel/place/v1` | `ILwcCancelOrder` | Implemented (`cancel_order`) |

#### Cancel-Replace Orders (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/orderentry/cancelandreplace/preview/v1` | `ILwcReplaceOrder` | Implemented (`cancel_replace`) |
| POST | `/orderentry/cancelandreplace/place/v1` | `ILwcReplaceOrder` | Implemented (`cancel_replace`) |

#### Conditional Orders (4 endpoints — TWO base paths)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/orderentry/conditional/preview/v1` | `ILwcConditionalOrder` | Implemented (`conditional_orders`) |
| POST | `/orderentry/conditional/place/v1` | `ILwcConditionalOrder` | Implemented (`conditional_orders`) |
| POST | `/retail-condition-replace/v1/.../preview` | `ILwcConditionalReplaceOrder` | **MISSING** — different base path! |
| POST | `/retail-condition-replace/v1/.../place` | `ILwcConditionalReplaceOrder` | **MISSING** — different base path! |

#### Staged Orders (3 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/ent-research-staging/v1/.../staged-order/get` | `ILwcStagedOrders` | Implemented (`staged_orders`) |
| POST | `/ent-research-staging/v1/.../staged-order/save` | `ILwcStagedOrders` | **MISSING** |
| POST | `/ent-research-staging/v1/.../staged-order/delete` | `ILwcStagedOrders` | **MISSING** |

#### Tax Lots (1 endpoint)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/orderentry/taxlot/v1` | `ILwcSpecificShares` | Implemented (`tax_lots`) |

#### Closed Positions (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/customer-am-position/v1/.../closedposition` | `ILwcClosedPositions` | Implemented (`closed_positions`) |
| POST | `/customer-am-position/v1/.../closedlots` | `ILwcClosedPositions` | **MISSING** — closed tax lot detail |

#### Transactions (1 endpoint)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/accountmanagement/transaction/history/v2` | `ILwcAccountHistory` | Implemented (`transactions`) |

#### Loaned Securities (1 endpoint)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/retail-am-loanedsecurities/v1/.../rates` | `ILwcLoanedSecurities` | Implemented (`loaned_securities`) |

#### Watchlists (3 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/retail-watchlist/v1/.../get` | `ILwcWatchlist` | Implemented (`watchlists`) |
| POST | `/retail-watchlist/v1/.../save` | `ILwcWatchlist` | Partial (save only) |
| POST | `/retail-watchlist/v1/.../delete` | `ILwcWatchlist` | **MISSING** |

#### Price Triggers / Alerts (4 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/retail-price-triggers/v1/.../create` | `ILwcAlerts` | Implemented (`price_triggers`) |
| GET | `/retail-price-triggers/v1/.../list?status=active` | `ILwcAlerts` | Implemented (`price_triggers`) |
| GET | `/retail-price-triggers/v1/.../list?status=expired` | `ILwcAlerts` | Implemented (`price_triggers`) |
| POST | `/retail-price-triggers/v1/.../delete` | `ILwcAlerts` | Implemented (`price_triggers`) |

#### Legacy Alerts SOAP (2 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/alerts/services/ATBTSubscription` | `IAlertEmsSubscription` | Implemented (`alerts`) |
| POST | `/alerts/services/ATBTAlerts` | `IHistoricalAlertClient` | **MISSING** — historical alert query |

#### Research (3 endpoints)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| GET | `/ftgw/dpdirect/research/earning/v1` | `ILwcResearch` | Implemented (`research`) |
| GET | `/ftgw/dpdirect/research/dividend/v1` | `ILwcResearch` | Implemented (`research`) |
| POST | `/research/option/positions/analytics/v1` | `ILwcOptionAnalytics` | Implemented (`option_analytics`) |

#### Search (1 endpoint)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| GET | `/ftgw/dpdirect/search/autosuggest/v1` | `ILwcSearch` | Implemented (`search`) |

#### Option Summary (1 endpoint)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/retail-am-optionsummary/v1/.../get` | `ILwcOptionSummary` | Implemented (`option_summary`) |

#### Preferences (3 endpoints — TWO systems)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/.../atn-prefs/getpreference` | `ILwcPreference` | Implemented (`preferences`) |
| POST | `/.../atn-prefs/savepreference` | `ILwcPreference` | Implemented (`preferences`) |
| POST | `/retail-indepInvs-pref/v1/{get,save,delete}Preference` | `ILwcIiPreferenceApi` | **MISSING** — separate "II" preferences system |

#### Available Markets (1 endpoint)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/reference/security/stock/availablemarket/v1` | `ILwcAvailableMarkets` | Implemented (`available_markets`) |

#### Holiday Calendar (1 endpoint)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| GET | `/ftgw/dpdirect/market/holidaycalendar/v1` | `ILwcHolidayCalendar` | Implemented (`holiday_calendar`) |

#### Screener (1 endpoint — SAML auth)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `fidelity.apps.livevol.com/...ExecuteScan` | SAML flow | Implemented (`screener`) |

#### Short Insights (2 endpoints) — **NEW**

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/retail-am-shortinsight/v1/.../insights` | `ILwcShortInsights` | **MISSING** |
| POST | `/api/v1/timeseries` | `ILwcShortInsights` | **MISSING** |

#### Financing / Accruals (3 endpoints) — **NEW**

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/retail-am-accountaccruals/v1/accounts/accruals` | `ILwcAccruals` | **MISSING** |
| POST | `/retail-am-accountaccruals/v2/accounts/accruals` | `ILwcAccruals` | **MISSING** |
| POST | `/retail-am-accountaccruals/v1/accounts/cash/accruals` | `ILwcCashAccruals` | **MISSING** (uses `dpservicexq1` host!) |

#### Other NEW Endpoints

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/reference/security/stock/locate/find/v1` | `ILwcStockLocate` | **MISSING** — short sell locate |
| POST | `/trade/useragreement/modify/v1` | `ILwcTradeAgreement` | **MISSING** |
| GET | `/customer-paid-subscriptions/v1/.../subscriptions` | `ILwcSubscriptions` | **MISSING** — pro data status |
| POST | `/research/tool/notebook/note/{detail,create,delete,update}/v1` | `ILwcNotebook` | **MISSING** — 4 CRUD endpoints |
| GET | `/content-headless/v2/content` | `IHeadlessContent` | **MISSING** — CMS content |
| GET | `/security/token/authz/generate/1.0` | `ILwcAuthTokenApi` | **MISSING** — BEPS auth token |
| POST | `digital.fidelity.com/.../api/atprtm` | direct HttpClient | Skip — internal RTM |

#### Fastquote (Market Data)

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| GET | `/service/quote/chainLite` | XML/JSONP | Implemented (`option_chain`) |
| GET | `/service/quote/dtmontage` | XML/JSONP | Implemented (`option_chain`) |
| GET | `/service/marketdata/historical/chart/json` | JSON | Implemented (`chart`) |
| GET | `/service/timeandsales/v2` | XML | **MISSING** — T&S REST history |

#### Session Management

| Method | Path | Interface | SDK Status |
|--------|------|-----------|------------|
| POST | `/ftgw/digital/pico/api/v1/context/security` | direct | Implemented (`security_context`) |
| GET | `/ftgw/digital/portfolio/extendsession` | direct | Implemented (`session_keepalive`) |

---

## 3. MDDS Streaming Protocol

### Connection

- **URL:** `wss://mdds-i-tc.fidelity.com/?productid=atn`
- **Auth:** Session cookies forwarded via `Cookie` header on WebSocket open
- **TLS:** Accepts all certificates (no pinning)
- **First message from server:** `{"SessionId":"...", "host":"...", "productid":"..."}`
- **Valid when:** `SessionId` AND `ProductId` are both non-empty (no `Status` field)

### Commands (4 types)

| Command | Format | Use |
|---------|--------|-----|
| `subscribe` | `{"SessionId":"...","Command":"subscribe","Symbol":"AAPL,MSFT","ConflationRate":1000,"IncludeGreeks":false}` | Regular quote stream |
| `subscribe_virtualbook` | `{"SessionId":"...","Command":"subscribe_virtualbook","Symbol":"AAPL","ConflationRate":1000,"IncludeArcaOnly":true}` | L2 depth (25 levels) |
| `subscribe_1-minute-bar` | `{"SessionId":"...","Command":"subscribe_1-minute-bar","Symbol":"AAPL,MSFT","SessionId":"..."}` | 1-min OHLCV bars |
| `unsubscribe` | `{"SessionId":"...","Command":"unsubscribe","Request":"{requestId}"}` | Remove subscription (by request ID) |

### Connection Pool Architecture

The app runs **multiple simultaneous WebSocket connections**:

| Pool | Purpose | Initial Connections | Symbols Per Connection |
|------|---------|--------------------|-----------------------|
| Regular | Display quotes | 5 | 100 |
| TradeSafe | Trade validation quotes | separate | separate |
| VirtualBook | L2 depth | separate | 1 per symbol |
| Bar | 1-minute OHLCV | separate | varies |
| Scanner | Market screener | separate | varies |

- **Symbol chunking:** 50 symbols per subscribe message
- **Round-robin** load balancing across connections in a pool
- **Dynamic growth** up to `MaxConnectionCount`
- **Deferred unsubscribe:** 10-second delay with reference counting

### Reconnection Logic

Retry intervals: `[500, 1000, 2000, 3000, 4500, 10000, 30000]` ms
State machine: `None → Connecting → Open → Aborted → Reconnecting → Open`
On reconnect: checks internet connectivity + cookie validity before retrying

### Corrected Field ID Map (163 core fields)

The most critical fields — correcting ~20 errors in the current SDK:

| FID | Correct Name | SDK Had (WRONG) | Category |
|-----|-------------|-----------------|----------|
| **18** | **ask_price** | `open` | Quote |
| 19 | ask_size | — | Quote |
| 20 | bid_price | `bid` (correct) | Quote |
| 21 | bid_size | — | Quote |
| **23** | **block_trade_cum_vol** | `volume` | Volume |
| 26 | high_price | — | Quote |
| 27 | low_price | — | Quote |
| 28 | trade_size | — | T&S |
| **29** | **last_price** | `previous_close` | Quote |
| **31** | **open_price** | `ask` | Quote |
| **32** | **prev_close** | `close_price` | Quote |
| **33** | **volume (cum_vol)** | `total_volume` | Volume |
| 34 | dividend_yield | — | Fundamental |
| 43 | trade_exchange | — | T&S |
| 44 | trade_time | — | T&S |
| 45 | trade_conditions | — | T&S |
| 46 | avg_volume_10day | — | Volume |
| 57 | market_cap | — | Fundamental |
| 58 | pe_ratio | — | Fundamental |
| 60 | mid_price | — | Options |
| **100** | **bid_exchange** | `exchange_code` | Quote |
| **124** | **close** | `last_price` | Quote |
| **277** | **prev_ask_price** | `pre_market_price` | Extended |
| **278** | **prev_bid_price** | `pre_market_bid` | Extended |

**Greek Fields (correct — FIDs 187-191):**

| FID | Name | Status |
|-----|------|--------|
| 187 | delta | Correct |
| 188 | gamma | Correct |
| 189 | vega | Correct |
| 190 | theta | Correct |
| 191 | rho | Correct |
| 192 | intrinsic_value | **MISSING** |
| **193** | **time_value** | SDK has `premium` — wrong name |
| **195** | **iv_ask** | SDK has `implied_volatility` — wrong name |
| **196** | **iv_mid** | SDK has `historical_volatility` — wrong name |
| **290** | **iv_bid** | SDK has `intrinsic_value` — wrong mapping |

**Bar Fields (new — for 1-minute bars):**

| FID | Name |
|-----|------|
| 356 | bar_close_price |
| 357 | bar_end_time |
| 358 | bar_high_price |
| 359 | bar_low_price |
| 360 | bar_open_price |
| 361 | bar_start_time |
| 362 | bar_volume |
| 1172 | bar_trade_count |

**Time & Sales Fields (corrected):**

| Context | Fields |
|---------|--------|
| Regular session | `29` (LastPrice), `28` (TradeSize), `882` (TradeExchangeMic), `316` (LastPriceTime) |
| Irregular session | `1162` (IrrLastPrice), `1165` (IrrTradeSize), `1176` (IrrTradeExchangeMic), `1164` (IrrLastPriceTime) |
| SDK had (WRONG) | `1159-1165` range — incorrect |

**Symbol suffixes:**
- `.GK` = Greek data (strip to get option symbol)
- `.VB` = VirtualBook/L2 data (strip to get symbol)

---

## 4. BEPS GraphQL Event Streaming

A completely unimplemented real-time event system.

### Connection

- **Protocol:** GraphQL over WebSocket (`graphql-ws` subprotocol)
- **URL:** `wss://spservice.fidelity.com/graphql/realtime`
- **Auth:** Base64-encoded JSON `{"Authorization":"{token}","host":"{host}"}` in URL query parameter
- **Token source:** `GET /security/token/authz/generate/1.0` on dpservice
- **SDK library hint:** `x-amz-user-agent: aws-amplify/5.1.4 js` — built on AWS AppSync

### Message Flow

```
Client: {"type":"connection_init"}
Server: {"type":"connection_ack","payload":{"connectionTimeoutMs":300000}}
Client: {"id":"1","type":"start","payload":{"data":"{\"query\":\"subscription...\",\"variables\":{...}}","extensions":{"authorization":{...}}}}
Server: {"id":"1","type":"data","payload":{"data":{"subScribeBEPSEvent":{...}}}}
Server: {"type":"ka"}  (keepalive, every ~60s)
```

### GraphQL Schema

```graphql
subscription Subscription($subscribeId: String!, $consumerAppId: String!) {
    subScribeBEPSEvent(subscribeId: $subscribeId, consumerAppId: $consumerAppId) {
        eventId
        subscribeId
        source
        eventCreatedTime
        eventType
        handleTime
        hasError
        message
        desc
        consumerAppId
    }
}
```

### Event Types (20)

| Event Type | Category | Description |
|-----------|----------|-------------|
| MFCEX | Orders | Order execution (fill) |
| ORDUP | Orders | Order update |
| CXL01 | Orders | Order cancelled |
| SPPOS | Positions | Position change |
| SPBSM | Balances | Balance summary update |
| CBUPD | Positions | Cost basis update |
| TRPA / TRPB | Alerts | Price trigger alert (above/below) |
| MA50A / MA50B | Alerts | 50-day MA crossover alert |
| MA200A / MA200B | Alerts | 200-day MA crossover alert |
| 52WHA / 52WHB | Alerts | 52-week high/low alert |
| VOLAL | Alerts | Volume alert |
| ... | ... | ~20 total types |

### SDK Impact

This transforms the SDK from **polling** to **event-driven**. Instead of calling `order_status.get_orders()` repeatedly, subscribe once and receive `MFCEX` events when orders fill.

---

## 5. Data Models & Enums

### Key Enums (from decompiled source)

**OrderActionCode:**
`B` (Buy), `S` (Sell), `BO` (Buy to Open), `SO` (Sell to Open), `BC` (Buy to Close), `SC` (Sell to Close), `BH` (Buy to Cover), `SH` (Sell Short), `SA` (Sell All), `SS` (Specific Shares), `BP` (Buy Put), `SP` (Sell Put)

**TradeTifType:**
`Day`, `GTC`, `FOK` (Fill or Kill), `IOC` (Immediate or Cancel), `Day+Extended` (DayPlusDirectedTrading), `Day+Extended ARCX` (DayPlusNotDirectedTrading), `Good 'til 9:25` (DT and non-DT variants), `Good 'til 9:28`, `MOC` (Market on Close), `MOO` (Market on Open)

**OrderStatus (wire codes):**
`OPEN`, `FILLED`, `PARTIAL_FILL`, `PENDING_CANCEL`, `VERIFIED_CANCEL`, `UNTRIGGERED_AWAITS_PRIMARY_TRIGGER`, `ERROR`, `SETTLEMENT_PENDING`, `VERIFIED_CANCEL_PARTIAL_FILL`, `EXECUTION_PENDING`, `TRIGGERED_OPEN`, `PENDING_CANCEL_PARTIAL_FILL`, `UNTRIGGERED_AWAITS_CONTINGENT_TRIGGER`

**SecurityType:**
`Equity`, `Index`, `MutualFund`, `Option`, `IntlEquity`, `Forex`, `Bond`, `MarketStats`, `Future`, `MoneyMarket`, `Annuity`, `DigitalCurrency`, `Unknown`, `Error`

**OptionStrategy (27 types):**
`CallsAndPuts`, `Calls`, `Puts`, `Butterfly`, `BuyWrite`, `Calendar`, `Collar`, `Combo`, `Condor`, `Diagonal`, `IronCondor`, `Ratio`, `Straddle`, `Strangle`, `Vertical`, `Roll`, `Custom`, `Spread`, `CustomOct`, `CoveredCall`, `ProtectivePut`, `ReverseConversion`, `ConvertibleHedge`, `Conversion`, `CoveredPut`, `HedgeCall`

**ConditionalOrderType:**
`Contingent` (0), `OCO` (1), `OTO` (2), `OTOCO` (3)

**ExpirationType:**
`Regular`, `Weekly`, `Quarterly`, `WednesdayWeekly`, `EndOfMonth`, `MondayWeekly`

**MarketSession:**
`HolidayOrWeekend`, `MarketClosed`, `PreMarket`, `MarketOpen`, `PostMarket`, `DayPlus`, `PreMarket925Am`, `PreMarket928Am`, `MarketBriefing`, `MarketOnTheOpen`, `MarketOnTheClose`

### Missing Model Fields (summary)

| SDK Model | SDK Fields | Decompiled Fields | Missing |
|-----------|-----------|-------------------|---------|
| `PositionDetail` | 9 | 25+ | 16 (including `currentDayTradingDetail`, `optionDetail`) |
| `AccountGainLossDetail` | 6 | 14+ | 8 (including `intradayTodaysgainloss`) |
| `SecurityDetail` | 4 | 12 | 8 |
| `BaseOrderDetail` | 10 | 18+ | 10 (including `cancelDetail`, `specificShrDetail`) |
| `PriceTypeDetail` | 5 | 14 | 9 (including `stopPrice`, `trailingStopAmt`) |
| `OrderIdDetail` | 3 | 6 | 3 (including `linkedOrderId`) |
| `OptionDetail` | 5 | 10 | 5 |
| `AcctValDetail` | 10 | 17 | 7 |
| **Total** | | | **~90+ fields** |

### Serialization

- **Library:** System.Text.Json (NOT Newtonsoft)
- **Property naming:** `[JsonPropertyName("camelCase")]` on every field
- **Number handling:** `decimal` for all financial amounts (SDK uses `float` — precision issue)
- **Custom converters:** `JsonSerializerOptionsHelper` in `Fmr.ApiHeader` controls per-endpoint behavior
- **Required fields:** `requiredJsonProperties` list forces certain fields to always serialize (even if null/default)
- **Cancel-replace quirk:** `PriceTypeDetailReplaceReq` uses `string` (not decimal) for `limitPrice`/`stopPrice`

---

## 6. Configuration Schemas

The app ships with **65+ JSON configuration files** containing field definitions:

### Scanner Types (25 built-in scanners)

| Category | Scanners |
|----------|----------|
| **Markets** (8) | 52-Week High, 52-Week Low, High Social Sentiment, Low Social Sentiment, Pre-Session, Post-Session, Standard Session, Volume Movers |
| **Options** (6) | Exploding IV30, Imploding IV30, High Call Volume, High Put Volume, OTM Calls on Offer, OTM Puts on Offer |
| **Technicals** (11) | Bullish/Bearish Morning Momentum, Bullish/Bearish Parabolic Crossover, Bollinger Band Upside/Downside Breakout, MA Crossover, RSI Turnover, Short-Term Uptrend/Downtrend, Stochastic Patterns, Uptrend/Downtrend |

### Balance Views by Account Type (9 variants)

`Cash`, `CashWithOptions`, `Margin`, `MarginWithOptions`, `LimitedMargin`, `LimitedMarginWithOptions`, `WPS`, `Crypto`, `MarginDebtProtection`

### Quote Views by Security Type (7 variants)

`Default`, `Equity`, `Option`, `Index`, `MutualFund`, `MoneyMarket`, `DigitalCurrency`

### Option Chain Preload Symbols

The app pre-fetches option chains for: **SPY, QQQ, SPX, NVDA, TSLA, AMD, IWM, AAPL, AMZN, META**

---

## 7. Feature Flags

**48 LaunchDarkly flags** (all prefixed `ATN-`). Most notable:

| Flag | Impact |
|------|--------|
| `ATN-Alert-Backend-Switch` | **HIGH** — controls TIBCO→BEPS alert migration. SDK should implement BEPS. |
| `ATN-NavBar-Agent-Icon` | **HIGH** — AI/Agent feature being rolled out in Trader+ |
| `ATN-Immediate-Position-Updates-V2` | **HIGH** — real-time position updates via BEPS execution events |
| `ATN-MinVersion-Upgrade` | **Medium** — pre-login version check, may force SDK User-Agent update |
| `ATN-Accruals-Rest-API-V2` | **Medium** — determines which accruals endpoint to use |
| `ATN-ProBilling-Enabled` | **Medium** — affects quote data entitlements |
| `ATN-Use-CrossSession-ExtHrsData` | **Medium** — affects extended hours data behavior |
| `ATN-Scanner-Options-Token` | **Medium** — options scanner auth |
| `ATN-Display-Crypto-In-TimeandSales` | **Medium** — crypto T&S support |

---

## 8. SDK Gap Analysis

### Coverage Summary

| Metric | Current SDK | Decompiled Total | Coverage |
|--------|------------|-----------------|----------|
| REST endpoints | ~52 | 88 | **59%** |
| Pydantic model fields | ~60% | 100% | **~60%** |
| MDDS field IDs | ~50 (20 wrong) | 335 | **15%** (correct: ~9%) |
| Streaming capabilities | 2 | 6 | **33%** |
| Enum coverage | partial | complete | **~40%** |

### 12 Critical Bugs Found

| # | Bug | Impact |
|---|-----|--------|
| B1 | MDDS field IDs wrong (~20 swaps) | Every streaming quote returns wrong data |
| B2 | ConnectResponse checks wrong field | Connection detection may fail |
| B3 | Time & Sales FIDs wrong | T&S data is garbage |
| B4 | Unsubscribe format wrong | Unsubscribe silently fails |
| B5 | `float` instead of `Decimal` | Financial precision errors |
| B6 | Cancel missing preview step | Users can't preview cancel consequences |
| B7 | Conditional replace wrong path | Would 404 on condition modification |
| B8 | User-Agent outdated (4.4.1.7 vs 4.5.1.4) | Version detection risk |
| B9 | Missing per-endpoint headers | Some endpoints may reject or degrade |
| B10 | Cancel-replace prices should be strings | Server may reject |
| B11 | Greek/IV field names wrong | IV values mislabeled |
| B12 | Missing IncludeGreeks auto-detect | Unnecessary server load for equities |

---

## 9. Implementation Roadmap

### Sprint 1 — Critical Fixes (8 items)

Fix MDDS field IDs, ConnectResponse, unsubscribe format, T&S FIDs, Greek names, symbol chunking, User-Agent, cancel-replace price types.

### Sprint 2 — Model Enrichment (10 items)

Add ~90 missing fields across Position, Order, Balance models. Add all missing enums. Add `Decimal` precision mode.

### Sprint 3 — New Endpoints (8 items)

Cancel preview, order detail, account features, conditional replace, open lots, closed lots, per-endpoint headers, customer subscriptions.

### Sprint 4 — Streaming (7 items)

Connection pool manager, reference counting, reconnect logic, Greek auto-detect, BEPS GraphQL client, 1-min bars, complete field map (335 FIDs).

### Sprint 5+ — Feature Parity (10 items)

Short insights, hard-to-borrow, financing/accruals, notebook CRUD, scanner streaming, TradeSafe dual stream, trade agreements, CMS content, II preferences, watchlist delete.

**Total: 45 items across ~5 sprints**

---

## 10. File Locations

### Decompiled Source

```
~/fidelity-decomp/
├── REPORT.md                          ← Executive summary
├── version.txt                        ← v4.5.1.4
├── manifest.txt                       ← Full DLL inventory
├── decompile.log                      ← Build log
├── src/                               ← 97 decompiled C# projects (8,784 files)
│   ├── Fidelity Trader+/             ← Main app entry point
│   ├── Fmr.Orders/                   ← 315 files
│   ├── Fmr.Trade/                    ← 482 files
│   ├── Fmr.Nebula/                   ← 672 files (data layer)
│   ├── Fmr.NovaUI/                   ← 661 files (UI framework)
│   └── ...                           ← 93 more projects
├── metadata/
│   ├── types.txt                     ← 5,599 public types
│   └── namespaces.txt                ← 1,544 namespaces
└── analysis/
    ├── sdk-reconciliation.md         ← Definitive gap analysis (866 lines)
    ├── api-endpoints.md              ← All 88 endpoints
    ├── data-models.md                ← All DTOs, enums, constants
    ├── protocols.md                  ← MDDS, BEPS, streaming specs
    ├── config-schemas.md             ← JSON config field dictionary
    └── state-architecture.md         ← Fluxor state tree, feature flags
```

### Application

```
C:\Program Files\WindowsApps\68D72461-B3DB-4FE2-AE47-50EF0FD7254F_4.5.1.4_x64__w2vdhxtqt7mse\
├── Fidelity Trader+.exe              ← Entry point
├── Fidelity Trader+.dll              ← Main assembly (917KB)
├── Fidelity Trader+.runtimeconfig.json ← .NET 10.0.3 config
├── Fidelity Trader+.deps.json        ← Dependency manifest
├── AppxManifest.xml                  ← MSIX manifest (FMR LLC publisher)
├── Fmr.*.dll                         ← 96 first-party assemblies
├── JSONs/                             ← 40+ view/scanner configs
├── Queries/BepsSubscription.graphql   ← GraphQL schema
├── Scripts/                           ← PowerShell install/update scripts
└── NpuDetect/                         ← AI/NPU workload detection
```

### Agent Definitions

```
.claude/agents/
├── decomp-orchestrator.md             ← Workflow coordinator
├── decompiler-setup.md                ← Phase 1: Bulk decompilation
├── config-miner.md                    ← Phase 2: JSON config analysis
├── api-surface-extractor.md           ← Phase 3: Refit/HTTP extraction
├── model-extractor.md                 ← Phase 4: DTO/enum extraction
├── protocol-decoder.md                ← Phase 5: Streaming protocols
├── state-flow-analyzer.md             ← Phase 6: Fluxor/DI analysis
├── sdk-reconciler.md                  ← Phase 7: Gap analysis
└── assembly-deep-diver.md             ← Ad-hoc single-assembly analysis
```
