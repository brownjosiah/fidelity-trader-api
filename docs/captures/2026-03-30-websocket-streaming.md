# WebSocket Streaming Discovery

Captured: 2026-03-30 from Fidelity Trader+ desktop app

## Streaming Hosts

| Host | Purpose | Protocol |
|------|---------|----------|
| `mdds-i.fidelity.com/?productid=atn` | Market Data Distribution (initial/handshake) | WebSocket |
| `mdds-i-tc.fidelity.com/?productid=atn` | Market Data Distribution (primary data feed) | WebSocket |
| `streaming-news.mds.fidelity.com/ftgw/snaz/Authorize` | News streaming auth (returns WebSocket creds for newsedge.net) | HTTP POST |
| `fid-str.newsedge.net:443` | News streaming data feed (not yet captured) | WebSocket (likely) |
| `fid-polling.newsedge.net:443` | News polling fallback | HTTP (likely) |

## MDDS WebSocket Protocol

### Connection
- URL: `wss://mdds-i-tc.fidelity.com/?productid=atn`
- On connect, server sends session info:
```json
{"Message":"success","SessionId":"a21af247-...","Status":"Ok","host":"7f5d436d3043.us-east-2a","productid":"atn"}
```

### Subscribe Command (client → server)
```json
{
  "SessionId": "a21af247-...",
  "Command": "subscribe",
  "Symbol": ".SPX,AAPL,MSFT,-SPXW260330P6330",
  "ConflationRate": 1000,
  "IncludeGreeks": true
}
```
- Symbols are comma-delimited
- Options use OCC format with dash prefix: `-SPXW260330P6330`
- Indices use dot prefix: `.SPX`, `.DJI`, `.TNX`
- `ConflationRate`: milliseconds between updates (1000 = 1/sec)
- `IncludeGreeks`: include option greeks in streaming data

### Subscribe Response (server → client)
Success (e.g., .SPX subscription):
```json
{
  "Command": "subscribe",
  "ResponseType": "1",
  "Data": [{
    "0": "success",
    "1": "S&P 500 INDEX",
    "10": "SPX",
    "11": "SPX",
    "12": "-25.13",
    "13": "-0.394577",
    "14": "7002.28",
    "15": "2026-01-28",
    "16": "4835.04",
    "17": "2025-04-07",
    "18": "6385...",
    "124": "6343.72",
    "128": "IX",
    "169": "realtime",
    ...
  }]
}
```

Error (expired option, etc.):
```json
{
  "Command": "subscribe",
  "ResponseType": "-1",
  "ErrorCode": "18",
  "Data": [{"0": "Source not found", "6": "-SPXW260217P6750"}]
}
```

### Field Number Mapping (partial — needs market-hours capture for full mapping)
Known from initial subscription response:
- `0`: status / description
- `1`: security name
- `10`: symbol (root)
- `11`: symbol (display)
- `12`: price change ($)
- `13`: price change (%)
- `14`: 52-week high
- `15`: 52-week high date
- `16`: 52-week low
- `17`: 52-week low date
- `124`: last price (likely)
- `128`: security type code
- `169`: data quality ("realtime" vs "delayed")

**TODO: Need market-hours capture to see streaming tick data with bid/ask/last/volume fields**

### Connection Architecture
The app opens MULTIPLE WebSocket connections:
- 2x `mdds-i.fidelity.com` (appear to be for handshake/session init only)
- 8-10x `mdds-i-tc.fidelity.com` (primary data channels, each subscribing to different symbol batches)

Symbols are split across connections, likely for load balancing.

### Key Observations
1. This is the **real-time quote system** — not a REST API. Fidelity Trader+ gets ALL price data through these WebSockets, not REST endpoints.
2. The field numbering suggests a proprietary binary/tagged protocol encoded as JSON.
3. Expired options return ErrorCode 18 ("Source not found").
4. Sessions are region-aware (us-east-1c, us-east-2a, us-east-2b).
5. No additional auth beyond cookies — the WebSocket connection inherits the session cookies from login.

## Next Capture Steps
1. **Market hours capture** — capture during trading hours to see real tick data flowing (bid, ask, last, volume, Greeks)
2. **Full field mapping** — subscribe to a single equity + option and document all field numbers
3. **Unsubscribe command** — capture what happens when switching watchlists or closing a chart
4. **News streaming** — connect to newsedge.net with the access token from the Authorize endpoint
