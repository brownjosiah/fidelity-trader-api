# Fidelity Trader SDK

## Project Overview
Unofficial Python SDK that replicates the Fidelity Trader+ desktop application's API calls as an extensible Python library. Built by reverse-engineering network traffic via mitmproxy captures.

## Architecture
- **`src/fidelity_trader/client.py`** — Main `FidelityClient` entry point, composes all modules
- **`src/fidelity_trader/auth/session.py`** — 7-step login handshake against `ecaap.fidelity.com`
- **`src/fidelity_trader/trading/`** — Order placement, modification, cancellation (TODO)
- **`src/fidelity_trader/portfolio/`** — Positions, balances, account info (TODO)
- **`src/fidelity_trader/market_data/`** — Quotes, charts, watchlists (TODO)

## Key Technical Details

### API Hosts
- `digital.fidelity.com` — Login page init, static assets, logging
- `ecaap.fidelity.com` — Authentication and session management API
- Additional hosts TBD as more traffic is captured

### Authentication Flow
The login is a 7-step handshake (see `auth/session.py` docstring for full sequence). Key points:
- Each request needs a unique `fsreqid: REQ{uuid}` header
- The `ET` cookie is the auth token, passed between steps
- After session creation, `ATC`, `FC`, `RC`, `SC` cookies are set for authenticated requests
- Headers `AppId: RETAIL-CC-LOGIN-SDK` and `AppName: PILoginExperience` are required
- User-Agent must include `ATPNext/4.4.1.7 FTPlusDesktop/4.4.1.7`

### HTTP Client
Uses `httpx` (sync) with cookie persistence across requests. The client handles cookie jar management automatically.

## Development

### Setup
```bash
pip install -e ".[dev]"
```

### Testing
```bash
pytest
```

### Capture Workflow
When adding new API modules:
1. Start mitmproxy: `mitmweb --listen-port 8080 -w capture.flow`
2. Set system proxy to `127.0.0.1:8080`
3. Use Fidelity Trader+ and perform the target action
4. Filter captures: `mitmdump -n -r capture.flow -s filter_script.py`
5. Map the API sequence and implement in the appropriate module

### Capture filter script location
`~/fidelity_filter.py` — mitmproxy addon script that filters to Fidelity API calls (ecaap + /prgw/ endpoints)

## Code Conventions
- Use `httpx` for all HTTP calls (not requests)
- Use `pydantic` models for API response types
- Each module follows the pattern: capture traffic → map endpoints → implement in SDK
- Keep credentials out of code — never hardcode usernames/passwords
- Capture files (*.flow, *.har) are gitignored

## Useful Commands
```bash
# Replay captured flows
mitmdump -n -r ~/fidelity_capture.flow --replay-client

# Filter Fidelity traffic from a capture
mitmdump -n -r capture.flow -s ~/fidelity_filter.py

# Export to HAR
mitmdump -n -r capture.flow --set hardump=output.har
```
