# Fidelity Trader+ SDK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive Python SDK that replicates every API endpoint available from the Fidelity Trader+ desktop application, enabling programmatic access to authentication, account data, market data, options chains, trading, and real-time streaming.

**Architecture:** Pure HTTP client using `httpx` with cookie-based session management. No browser automation — login is done via direct API calls to `ecaap.fidelity.com`, then authenticated requests hit `digital.fidelity.com` REST endpoints. Pydantic models for all request/response types. Modular design: each API domain (auth, quotes, options, trading, portfolio) is a standalone module composed by a top-level `FidelityClient`.

**Tech Stack:** Python 3.10+, httpx, pydantic v2, pytest, respx

---

## Known API Surface (from fidelity-api repo + mitmproxy captures)

### Hosts
- `ecaap.fidelity.com` — Authentication, session management
- `digital.fidelity.com` — All data and trading endpoints

### Discovered Endpoints

**Authentication (ecaap.fidelity.com):**
- `DELETE /user/session/login` — Clear existing session
- `GET /user/identity/remember/username` — Check remembered username
- `POST /user/identity/remember/username/1` — Select remembered user
- `POST /user/factor/password/authentication` — Submit credentials
- `PUT /user/identity/remember/username` — Update remembered user
- `POST /user/session/login` — Create authenticated session

**Session/Tokens (digital.fidelity.com):**
- `GET /prgw/digital/login/atp` — Init login page, get session cookies
- `GET /prgw/digital/research/api/tokens` — Get CSRF token for trading endpoints

**Quotes (digital.fidelity.com, cookie-only):**
- `GET /ftgw/digital/options-research/api/quotes?symbols=` — Real-time quotes
- `GET /ftgw/digital/traderplus-api/api/quotes` — Alternate quote source

**Options (digital.fidelity.com, cookie-only):**
- `GET /ftgw/digital/options-research/api/option-expirations?symbol=` — Expiration dates
- `GET /ftgw/digital/options-research/api/slo-chain` — Single-leg option chain with Greeks
- `GET /ftgw/digital/options-research/api/mlo-chain` — Multi-leg option chain (spreads)
- `GET /ftgw/digital/options-research/api/volatility-extended` — HV/IV data
- `GET /ftgw/digital/options-research/api/key-statistics` — Option statistics
- `GET /ftgw/digital/options-research/api/research-data` — Research data

**Accounts (digital.fidelity.com, cookie-only or CSRF):**
- `POST /ftgw/digital/pico/api/v1/context/account` — Discover all accounts
- `GET /ftgw/digital/options-research/api/account-positions` — Positions (research view)
- `GET /ftgw/digital/traderplus-api/api/accounts` — Account list (traderplus)
- `GET /ftgw/digital/traderplus-api/api/positions` — Positions (traderplus)

**Trading (digital.fidelity.com, CSRF required):**
- `POST /ftgw/digital/trade-options/api/balances` — Account balances + buying power
- `POST /ftgw/digital/trade-options/api/positions` — Trading positions
- `GET /ftgw/digital/trade-options/api/rules-engine` — Trading rules, option levels
- `GET /ftgw/digital/trade-options/api/config` — Trade configuration
- `POST /ftgw/digital/trade-options/api/account-fusion` — Account fusion data
- `GET /ftgw/digital/trade-options/api/autosuggest` — Symbol autosuggest

**Yet to capture (need mitmproxy sessions):**
- Order placement / preview / submit
- Order modification / cancellation
- Order status / history
- Watchlists CRUD
- Alerts CRUD
- Streaming/WebSocket feeds (if any)
- Statements / tax documents
- Transfer endpoints

---

## File Structure

```
src/fidelity_trader/
├── __init__.py                    # Exports FidelityClient
├── client.py                      # Main FidelityClient, composes all modules
├── exceptions.py                  # All custom exceptions
├── _http.py                       # Shared HTTP session factory + helpers
├── models/
│   ├── __init__.py
│   ├── auth.py                    # Login response models
│   ├── account.py                 # Account, balance, position models
│   ├── quote.py                   # Quote response models
│   ├── option.py                  # Option chain, expiration, greeks models
│   └── order.py                   # Order request/response models (future)
├── auth/
│   ├── __init__.py
│   └── session.py                 # 7-step login + CSRF token management
├── accounts/
│   ├── __init__.py
│   └── accounts.py                # Account discovery, balances, positions
├── market_data/
│   ├── __init__.py
│   └── quotes.py                  # Quotes for equities, indices, options
├── options/
│   ├── __init__.py
│   └── chains.py                  # Option chains, expirations, volatility
├── trading/
│   ├── __init__.py
│   └── orders.py                  # Order placement, modification, history (future)
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures (mock HTTP, fake cookies)
├── test_auth.py                   # Auth flow tests
├── test_http.py                   # HTTP helper tests
├── test_accounts.py               # Account discovery + balance tests
├── test_quotes.py                 # Quote API tests
├── test_options.py                # Option chain tests
├── test_models.py                 # Pydantic model tests
```

---

## Task 1: Shared HTTP Layer + Exceptions

**Files:**
- Create: `src/fidelity_trader/exceptions.py`
- Create: `src/fidelity_trader/_http.py`
- Create: `tests/conftest.py`
- Create: `tests/test_http.py`
- Modify: `src/fidelity_trader/auth/session.py` (remove inline `AuthenticationError`)

- [ ] **Step 1: Write failing test for HTTP session factory**

```python
# tests/test_http.py
import httpx
from fidelity_trader._http import create_session, REQUEST_HEADERS

def test_create_session_returns_httpx_client():
    client = create_session()
    assert isinstance(client, httpx.Client)
    assert client.headers["AppId"] == "RETAIL-CC-LOGIN-SDK"
    client.close()

def test_create_session_has_required_headers():
    client = create_session()
    assert "ATPNext" in client.headers["User-Agent"]
    assert client.headers["Content-Type"] == "application/json"
    client.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_http.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fidelity_trader._http'`

- [ ] **Step 3: Write exceptions module**

```python
# src/fidelity_trader/exceptions.py
class FidelityError(Exception):
    """Base exception for all SDK errors."""

class AuthenticationError(FidelityError):
    """Login or session creation failed."""

class SessionExpiredError(FidelityError):
    """Session cookies are no longer valid."""

class CSRFTokenError(FidelityError):
    """Failed to obtain CSRF token for protected endpoints."""

class APIError(FidelityError):
    """Fidelity API returned an unexpected error."""
    def __init__(self, message: str, status_code: int = None, response_body: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
```

- [ ] **Step 4: Write HTTP session factory**

```python
# src/fidelity_trader/_http.py
import uuid
import httpx

BASE_URL = "https://digital.fidelity.com"
AUTH_URL = "https://ecaap.fidelity.com"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0 "
        "ATPNext/4.4.1.7 FTPlusDesktop/4.4.1.7"
    ),
    "AppId": "RETAIL-CC-LOGIN-SDK",
    "AppName": "PILoginExperience",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "Accept-Token-Type": "ET",
    "Accept-Token-Location": "HEADER",
    "Token-Location": "HEADER",
    "Cache-Control": "no-cache, no-store, must-revalidate",
}

def create_session(timeout: float = 30.0) -> httpx.Client:
    """Create a pre-configured httpx client for Fidelity APIs."""
    return httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers=REQUEST_HEADERS,
    )

def make_req_id() -> str:
    """Generate a unique request ID in Fidelity's format."""
    return f"REQ{uuid.uuid4().hex}"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_http.py -v`
Expected: PASS

- [ ] **Step 6: Write shared test fixtures**

```python
# tests/conftest.py
import httpx
import pytest
import respx

from fidelity_trader._http import BASE_URL, AUTH_URL

@pytest.fixture
def mock_http():
    """Provide a fresh httpx.Client for testing."""
    client = httpx.Client()
    yield client
    client.close()

@pytest.fixture
def fidelity_response():
    """Factory for Fidelity-style API responses."""
    def _make(message: str, code: int = 1200, **extra):
        resp = {
            "responseBaseInfo": {
                "sessionTokens": None,
                "status": {"code": code, "message": message},
                "links": [],
            }
        }
        resp.update(extra)
        return resp
    return _make
```

- [ ] **Step 7: Update auth/session.py to use shared modules**

Replace the inline `AuthenticationError` import and `_req_id` helper:

```python
# src/fidelity_trader/auth/session.py - updated imports
import httpx

from fidelity_trader._http import make_req_id
from fidelity_trader.exceptions import AuthenticationError
```

Remove the `_req_id` function and `AuthenticationError` class from `auth/session.py`. Replace all calls to `_req_id()` with `make_req_id()`.

- [ ] **Step 8: Update existing tests to use conftest fixtures**

```python
# tests/test_auth.py - update to use conftest
import httpx
import pytest
import respx

from fidelity_trader._http import BASE_URL, AUTH_URL
from fidelity_trader.auth.session import AuthSession
from fidelity_trader.exceptions import AuthenticationError

@respx.mock
def test_login_success(fidelity_response):
    respx.get(f"{BASE_URL}/prgw/digital/login/atp").mock(
        return_value=httpx.Response(200, text="<html>login</html>")
    )
    respx.delete(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Authenticated"))
    )
    respx.put(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("OK"))
    )
    respx.post(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(
            200, json=fidelity_response("Session Created", authenticators=[])
        )
    )

    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)
    result = auth.login("testuser", "testpass")

    assert auth.is_authenticated
    assert result["responseBaseInfo"]["status"]["message"] == "Session Created"
    client.close()

@respx.mock
def test_login_bad_password(fidelity_response):
    respx.get(f"{BASE_URL}/prgw/digital/login/atp").mock(
        return_value=httpx.Response(200)
    )
    respx.delete(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Identified"))
    )
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(
            200, json=fidelity_response("Authentication Failed", code=1400)
        )
    )

    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)

    with pytest.raises(AuthenticationError, match="Authentication Failed"):
        auth.login("testuser", "wrongpass")

    assert not auth.is_authenticated
    client.close()
```

- [ ] **Step 9: Run all tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 10: Commit**

```bash
git add src/fidelity_trader/exceptions.py src/fidelity_trader/_http.py tests/conftest.py tests/test_http.py src/fidelity_trader/auth/session.py tests/test_auth.py
git commit -m "refactor: extract shared HTTP layer, exceptions, and test fixtures"
```

---

## Task 2: Pydantic Models — Auth & Account

**Files:**
- Create: `src/fidelity_trader/models/__init__.py`
- Create: `src/fidelity_trader/models/auth.py`
- Create: `src/fidelity_trader/models/account.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing test for auth models**

```python
# tests/test_models.py
from fidelity_trader.models.auth import FidelityStatus, LoginResponse

def test_fidelity_status_parses():
    raw = {"code": 1200, "message": "User Authenticated", "requestIdentifier": "REQabc123"}
    status = FidelityStatus.model_validate(raw)
    assert status.code == 1200
    assert status.message == "User Authenticated"
    assert status.is_success

def test_fidelity_status_failure():
    raw = {"code": 1400, "message": "Authentication Failed"}
    status = FidelityStatus.model_validate(raw)
    assert not status.is_success

def test_login_response_parses():
    raw = {
        "responseBaseInfo": {
            "sessionTokens": None,
            "status": {"code": 1200, "message": "Session Created"},
            "links": [],
        },
        "authenticators": [],
        "location": None,
        "referenceId": None,
        "callbacks": [],
        "isPreferredAuthenticatorUnavailable": False,
    }
    resp = LoginResponse.model_validate(raw)
    assert resp.status.is_success
    assert resp.status.message == "Session Created"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_models.py::test_fidelity_status_parses -v`
Expected: FAIL

- [ ] **Step 3: Implement auth models**

```python
# src/fidelity_trader/models/__init__.py
from fidelity_trader.models.auth import FidelityStatus, LoginResponse
from fidelity_trader.models.account import Account, Balance, Position

__all__ = [
    "FidelityStatus", "LoginResponse",
    "Account", "Balance", "Position",
]
```

```python
# src/fidelity_trader/models/auth.py
from pydantic import BaseModel, Field
from typing import Optional

class FidelityStatus(BaseModel):
    code: int
    message: str
    request_identifier: Optional[str] = Field(None, alias="requestIdentifier")
    context: Optional[str] = Field(None, alias="Context")

    @property
    def is_success(self) -> bool:
        return self.code == 1200

class ResponseBaseInfo(BaseModel):
    session_tokens: Optional[dict] = Field(None, alias="sessionTokens")
    status: FidelityStatus
    links: list = Field(default_factory=list)

class LoginResponse(BaseModel):
    response_base_info: ResponseBaseInfo = Field(alias="responseBaseInfo")
    authenticators: list = Field(default_factory=list)
    location: Optional[str] = None
    reference_id: Optional[str] = Field(None, alias="referenceId")
    callbacks: list = Field(default_factory=list)

    @property
    def status(self) -> FidelityStatus:
        return self.response_base_info.status
```

- [ ] **Step 4: Run auth model tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_models.py -v -k auth`
Expected: PASS

- [ ] **Step 5: Write account model tests**

Add to `tests/test_models.py`:

```python
from fidelity_trader.models.account import Account, Balance, Position

def test_account_parses():
    raw = {
        "acctNum": "Z12345678",
        "acctType": "Brokerage",
        "acctSubType": "Brokerage",
        "acctSubTypeDesc": "Individual",
        "preferenceDetail": {"acctNickName": "My Trading"},
        "acctTradeAttrDetail": {
            "optionLevel": 5,
            "mrgnEstb": True,
            "optionEstb": True,
        },
    }
    acct = Account.model_validate(raw)
    assert acct.acct_num == "Z12345678"
    assert acct.nickname == "My Trading"
    assert acct.option_level == 5
    assert acct.is_margin
    assert acct.is_options_enabled

def test_balance_parses():
    raw = {
        "totalAcctVal": "125000.50",
        "cashAvailForTrade": "45000.00",
        "intraDayBP": "90000.00",
        "isMrgnAcct": True,
    }
    bal = Balance.model_validate(raw)
    assert bal.total_account_value == 125000.50
    assert bal.cash_available == 45000.00
    assert bal.intraday_buying_power == 90000.00

def test_position_parses():
    raw = {
        "symbol": "AAPL",
        "securityType": "Equity",
        "quantity": "100",
        "lastPrice": "178.50",
        "marketValue": "17850.00",
        "costBasis": "15000.00",
        "gainLoss": "2850.00",
        "gainLossPct": "19.00",
    }
    pos = Position.model_validate(raw)
    assert pos.symbol == "AAPL"
    assert pos.quantity == 100.0
    assert pos.market_value == 17850.0
```

- [ ] **Step 6: Implement account models**

```python
# src/fidelity_trader/models/account.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional

def _parse_float(v) -> Optional[float]:
    if v is None or v == "" or v == "--" or v == "N/A":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).replace(",", ""))

def _parse_int(v) -> Optional[int]:
    if v is None or v == "" or v == "--" or v == "N/A":
        return None
    if isinstance(v, int):
        return v
    return int(str(v).replace(",", ""))

class Account(BaseModel):
    acct_num: str = Field(alias="acctNum")
    acct_type: str = Field(alias="acctType")
    acct_sub_type: str = Field("", alias="acctSubType")
    acct_sub_type_desc: str = Field("", alias="acctSubTypeDesc")
    nickname: str = ""
    option_level: int = 0
    is_margin: bool = False
    is_options_enabled: bool = False
    is_retirement: bool = False

    @classmethod
    def model_validate(cls, obj, **kwargs):
        if isinstance(obj, dict):
            pref = obj.get("preferenceDetail", {})
            trade = obj.get("acctTradeAttrDetail", {})
            obj = {
                **obj,
                "nickname": pref.get("acctNickName", ""),
                "option_level": trade.get("optionLevel", 0),
                "is_margin": trade.get("mrgnEstb", False),
                "is_options_enabled": trade.get("optionEstb", False),
                "is_retirement": obj.get("acctType", "") in ("IRA", "Roth IRA", "401k"),
            }
        return super().model_validate(obj, **kwargs)

class Balance(BaseModel):
    total_account_value: Optional[float] = Field(None, alias="totalAcctVal")
    cash_available: Optional[float] = Field(None, alias="cashAvailForTrade")
    intraday_buying_power: Optional[float] = Field(None, alias="intraDayBP")
    margin_buying_power: Optional[float] = Field(None, alias="mrgnBP")
    non_margin_buying_power: Optional[float] = Field(None, alias="nonMrgnBP")
    is_margin_account: bool = Field(False, alias="isMrgnAcct")

    @field_validator(
        "total_account_value", "cash_available", "intraday_buying_power",
        "margin_buying_power", "non_margin_buying_power",
        mode="before",
    )
    @classmethod
    def parse_numeric(cls, v):
        return _parse_float(v)

class Position(BaseModel):
    symbol: str
    security_type: str = Field("", alias="securityType")
    quantity: Optional[float] = None
    last_price: Optional[float] = Field(None, alias="lastPrice")
    market_value: Optional[float] = Field(None, alias="marketValue")
    cost_basis: Optional[float] = Field(None, alias="costBasis")
    gain_loss: Optional[float] = Field(None, alias="gainLoss")
    gain_loss_pct: Optional[float] = Field(None, alias="gainLossPct")

    @field_validator(
        "quantity", "last_price", "market_value", "cost_basis",
        "gain_loss", "gain_loss_pct",
        mode="before",
    )
    @classmethod
    def parse_numeric(cls, v):
        return _parse_float(v)
```

- [ ] **Step 7: Run all model tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_models.py -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add src/fidelity_trader/models/ tests/test_models.py
git commit -m "feat: add pydantic models for auth responses, accounts, balances, positions"
```

---

## Task 3: CSRF Token Management

**Files:**
- Modify: `src/fidelity_trader/auth/session.py` (add CSRF token fetching)
- Create: `tests/test_csrf.py`

- [ ] **Step 1: Write failing test for CSRF token**

```python
# tests/test_csrf.py
import httpx
import respx

from fidelity_trader._http import BASE_URL, AUTH_URL
from fidelity_trader.auth.session import AuthSession

@respx.mock
def test_get_csrf_token():
    respx.get(f"{BASE_URL}/prgw/digital/research/api/tokens").mock(
        return_value=httpx.Response(200, json={"csrfToken": "abc123token"})
    )

    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)
    token = auth.get_csrf_token()
    assert token == "abc123token"
    client.close()

@respx.mock
def test_csrf_token_cached():
    route = respx.get(f"{BASE_URL}/prgw/digital/research/api/tokens").mock(
        return_value=httpx.Response(200, json={"csrfToken": "abc123token"})
    )

    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)
    auth.get_csrf_token()
    auth.get_csrf_token()
    assert route.call_count == 1
    client.close()

@respx.mock
def test_csrf_headers():
    respx.get(f"{BASE_URL}/prgw/digital/research/api/tokens").mock(
        return_value=httpx.Response(200, json={"csrfToken": "abc123token"})
    )

    client = httpx.Client()
    auth = AuthSession(client, BASE_URL, AUTH_URL)
    headers = auth.csrf_headers()
    assert headers["X-CSRF-TOKEN"] == "abc123token"
    client.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_csrf.py -v`
Expected: FAIL

- [ ] **Step 3: Add CSRF methods to AuthSession**

Add to `src/fidelity_trader/auth/session.py`:

```python
from fidelity_trader.exceptions import CSRFTokenError

# Inside AuthSession class, add:

    def __init__(self, http, base_url, auth_url):
        self._http = http
        self._base_url = base_url
        self._auth_url = auth_url
        self._authenticated = False
        self._csrf_token: str | None = None

    def get_csrf_token(self) -> str:
        """Fetch CSRF token from Fidelity's token endpoint. Caches the result."""
        if self._csrf_token:
            return self._csrf_token
        resp = self._http.get(f"{self._base_url}/prgw/digital/research/api/tokens")
        if resp.status_code != 200:
            raise CSRFTokenError(f"Failed to fetch CSRF token: {resp.status_code}")
        data = resp.json()
        self._csrf_token = data["csrfToken"]
        return self._csrf_token

    def csrf_headers(self) -> dict[str, str]:
        """Get headers dict with CSRF token for protected endpoints."""
        return {"X-CSRF-TOKEN": self.get_csrf_token()}

    def invalidate_csrf(self) -> None:
        """Force re-fetch of CSRF token on next request."""
        self._csrf_token = None
```

- [ ] **Step 4: Run tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_csrf.py tests/test_auth.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/fidelity_trader/auth/session.py tests/test_csrf.py
git commit -m "feat: add CSRF token management for protected trading endpoints"
```

---

## Task 4: Account Discovery & Balances Module

**Files:**
- Create: `src/fidelity_trader/accounts/accounts.py`
- Modify: `src/fidelity_trader/accounts/__init__.py`
- Create: `tests/test_accounts.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_accounts.py
import httpx
import respx

from fidelity_trader._http import BASE_URL
from fidelity_trader.accounts.accounts import AccountsAPI

CSRF_TOKEN = "test-csrf-token"

@respx.mock
def test_discover_accounts():
    respx.post(f"{BASE_URL}/ftgw/digital/pico/api/v1/context/account").mock(
        return_value=httpx.Response(200, json={
            "acctDetails": [
                {
                    "acctNum": "Z12345678",
                    "acctType": "Brokerage",
                    "acctSubType": "Brokerage",
                    "acctSubTypeDesc": "Individual",
                    "preferenceDetail": {"acctNickName": "Trading"},
                    "acctTradeAttrDetail": {"optionLevel": 5, "mrgnEstb": True, "optionEstb": True},
                },
                {
                    "acctNum": "Z99999999",
                    "acctType": "IRA",
                    "acctSubType": "IRA",
                    "acctSubTypeDesc": "Traditional IRA",
                    "preferenceDetail": {"acctNickName": "Retirement"},
                    "acctTradeAttrDetail": {"optionLevel": 2, "mrgnEstb": False, "optionEstb": True},
                },
            ]
        })
    )

    client = httpx.Client()
    api = AccountsAPI(client)
    accounts = api.discover_accounts()
    assert len(accounts) == 2
    assert accounts[0].acct_num == "Z12345678"
    assert accounts[0].is_margin
    assert accounts[1].is_retirement
    client.close()

@respx.mock
def test_get_balances():
    respx.post(f"{BASE_URL}/ftgw/digital/trade-options/api/balances").mock(
        return_value=httpx.Response(200, json={
            "totalAcctVal": "125000.50",
            "cashAvailForTrade": "45000.00",
            "intraDayBP": "90000.00",
            "isMrgnAcct": True,
        })
    )

    client = httpx.Client()
    api = AccountsAPI(client, csrf_token=CSRF_TOKEN)
    balance = api.get_balances("Z12345678")
    assert balance.total_account_value == 125000.50
    assert balance.cash_available == 45000.00
    client.close()

@respx.mock
def test_get_positions():
    respx.post(f"{BASE_URL}/ftgw/digital/trade-options/api/positions").mock(
        return_value=httpx.Response(200, json={
            "positionDetails": [
                {
                    "symbol": "AAPL",
                    "securityType": "Equity",
                    "quantity": "100",
                    "lastPrice": "178.50",
                    "marketValue": "17850.00",
                    "costBasis": "15000.00",
                    "gainLoss": "2850.00",
                    "gainLossPct": "19.00",
                },
            ],
        })
    )

    client = httpx.Client()
    api = AccountsAPI(client, csrf_token=CSRF_TOKEN)
    positions = api.get_positions("Z12345678")
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].quantity == 100.0
    client.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_accounts.py -v`
Expected: FAIL

- [ ] **Step 3: Implement AccountsAPI**

```python
# src/fidelity_trader/accounts/accounts.py
import httpx

from fidelity_trader._http import BASE_URL
from fidelity_trader.models.account import Account, Balance, Position
from fidelity_trader.exceptions import APIError


class AccountsAPI:
    """Account discovery, balances, and positions."""

    def __init__(self, http: httpx.Client, csrf_token: str = None) -> None:
        self._http = http
        self._csrf_token = csrf_token
        self._accounts: list[Account] = []

    def _csrf_headers(self) -> dict[str, str]:
        if not self._csrf_token:
            raise APIError("CSRF token required for this endpoint")
        return {"X-CSRF-TOKEN": self._csrf_token}

    def discover_accounts(self) -> list[Account]:
        """Discover all accounts via the account context endpoint."""
        resp = self._http.post(
            f"{BASE_URL}/ftgw/digital/pico/api/v1/context/account",
            json={},
        )
        resp.raise_for_status()
        data = resp.json()
        self._accounts = [
            Account.model_validate(acct)
            for acct in data.get("acctDetails", [])
        ]
        return self._accounts

    def get_account(self, acct_num: str) -> Account:
        """Get a specific account. Discovers if needed."""
        if not self._accounts:
            self.discover_accounts()
        for acct in self._accounts:
            if acct.acct_num == acct_num:
                return acct
        raise APIError(f"Account {acct_num} not found")

    def get_balances(self, acct_num: str) -> Balance:
        """Get account balances and buying power (CSRF required)."""
        acct = self.get_account(acct_num) if self._accounts else None
        body = {
            "account": {
                "acctNum": acct_num,
                "isDefaultAcct": False,
                "accountDetails": {
                    "acctType": acct.acct_type if acct else "Brokerage",
                    "acctSubType": acct.acct_sub_type if acct else "Brokerage",
                    "acctSubTypeDesc": acct.acct_sub_type_desc if acct else "",
                    "name": acct.nickname if acct else "",
                    "isRetirement": acct.is_retirement if acct else False,
                },
                "optionLevel": acct.option_level if acct else 0,
                "isMarginEstb": acct.is_margin if acct else False,
                "isOptionEstb": acct.is_options_enabled if acct else False,
            }
        }
        resp = self._http.post(
            f"{BASE_URL}/ftgw/digital/trade-options/api/balances",
            json=body,
            headers=self._csrf_headers(),
        )
        resp.raise_for_status()
        return Balance.model_validate(resp.json())

    def get_positions(self, acct_num: str) -> list[Position]:
        """Get open positions for an account (CSRF required)."""
        acct = self.get_account(acct_num) if self._accounts else None
        body = {
            "acctNum": acct_num,
            "acctType": acct.acct_type if acct else "Brokerage",
            "acctSubType": acct.acct_sub_type if acct else "Brokerage",
            "retirementInd": acct.is_retirement if acct else False,
        }
        resp = self._http.post(
            f"{BASE_URL}/ftgw/digital/trade-options/api/positions",
            json=body,
            headers=self._csrf_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            Position.model_validate(p)
            for p in data.get("positionDetails", [])
        ]
```

```python
# src/fidelity_trader/accounts/__init__.py
from fidelity_trader.accounts.accounts import AccountsAPI

__all__ = ["AccountsAPI"]
```

- [ ] **Step 4: Run tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_accounts.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/fidelity_trader/accounts/ tests/test_accounts.py
git commit -m "feat: add account discovery, balances, and positions API"
```

---

## Task 5: Market Data / Quotes Module

**Files:**
- Create: `src/fidelity_trader/market_data/quotes.py`
- Modify: `src/fidelity_trader/market_data/__init__.py`
- Create: `src/fidelity_trader/models/quote.py`
- Create: `tests/test_quotes.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_quotes.py
import httpx
import respx

from fidelity_trader._http import BASE_URL
from fidelity_trader.market_data.quotes import QuotesAPI

QUOTE_RESPONSE = {
    "quoteResponse": [
        {
            "status": "0",
            "requestSymbol": ".SPX",
            "quoteData": {
                "lastPrice": "5850.25",
                "dayHigh": "5875.00",
                "dayLow": "5820.00",
                "volume": "1234567",
                "netChgToday": "+15.50",
                "pctChgToday": "+0.27",
                "prevClosePrice": "5834.75",
                "openPrice": "5840.00",
            },
        }
    ]
}

@respx.mock
def test_get_quote():
    respx.get(f"{BASE_URL}/ftgw/digital/options-research/api/quotes").mock(
        return_value=httpx.Response(200, json=QUOTE_RESPONSE)
    )

    client = httpx.Client()
    api = QuotesAPI(client)
    quote = api.get_quote(".SPX")
    assert quote.last_price == 5850.25
    assert quote.day_high == 5875.00
    assert quote.symbol == ".SPX"
    client.close()

@respx.mock
def test_get_quotes_multiple():
    multi_response = {
        "quoteResponse": [
            {"status": "0", "requestSymbol": ".SPX", "quoteData": {"lastPrice": "5850.25"}},
            {"status": "0", "requestSymbol": ".VIX", "quoteData": {"lastPrice": "18.50"}},
        ]
    }
    respx.get(f"{BASE_URL}/ftgw/digital/options-research/api/quotes").mock(
        return_value=httpx.Response(200, json=multi_response)
    )

    client = httpx.Client()
    api = QuotesAPI(client)
    quotes = api.get_quotes([".SPX", ".VIX"])
    assert len(quotes) == 2
    assert quotes[".SPX"].last_price == 5850.25
    assert quotes[".VIX"].last_price == 18.50
    client.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_quotes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Quote model**

```python
# src/fidelity_trader/models/quote.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from fidelity_trader.models.account import _parse_float

class Quote(BaseModel):
    symbol: str = ""
    last_price: Optional[float] = Field(None, alias="lastPrice")
    day_high: Optional[float] = Field(None, alias="dayHigh")
    day_low: Optional[float] = Field(None, alias="dayLow")
    volume: Optional[int] = None
    net_change: Optional[float] = Field(None, alias="netChgToday")
    pct_change: Optional[float] = Field(None, alias="pctChgToday")
    prev_close: Optional[float] = Field(None, alias="prevClosePrice")
    open_price: Optional[float] = Field(None, alias="openPrice")
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = Field(None, alias="bidSize")
    ask_size: Optional[int] = Field(None, alias="askSize")

    @field_validator(
        "last_price", "day_high", "day_low", "net_change", "pct_change",
        "prev_close", "open_price", "bid", "ask",
        mode="before",
    )
    @classmethod
    def parse_float_fields(cls, v):
        return _parse_float(v)

    @field_validator("volume", "bid_size", "ask_size", mode="before")
    @classmethod
    def parse_int_fields(cls, v):
        if v is None or v == "" or v == "--":
            return None
        if isinstance(v, int):
            return v
        return int(str(v).replace(",", ""))
```

- [ ] **Step 4: Implement QuotesAPI**

```python
# src/fidelity_trader/market_data/quotes.py
import httpx

from fidelity_trader._http import BASE_URL
from fidelity_trader.models.quote import Quote


class QuotesAPI:
    """Real-time quote data from Fidelity."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_quote(self, symbol: str) -> Quote:
        """Get a real-time quote. Use '.SPX' for S&P 500, '.VIX' for VIX."""
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/options-research/api/quotes",
            params={"symbols": symbol},
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("quoteResponse", []):
            if item.get("status") == "0":
                quote_data = item.get("quoteData", {})
                quote = Quote.model_validate(quote_data)
                quote.symbol = item.get("requestSymbol", symbol)
                return quote
        return Quote(symbol=symbol)

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Get quotes for multiple symbols. Returns dict of symbol -> Quote."""
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/options-research/api/quotes",
            params={"symbols": ",".join(symbols)},
        )
        resp.raise_for_status()
        data = resp.json()
        result = {}
        for item in data.get("quoteResponse", []):
            if item.get("status") == "0":
                sym = item.get("requestSymbol", "")
                quote_data = item.get("quoteData", {})
                quote = Quote.model_validate(quote_data)
                quote.symbol = sym
                result[sym] = quote
        return result
```

```python
# src/fidelity_trader/market_data/__init__.py
from fidelity_trader.market_data.quotes import QuotesAPI

__all__ = ["QuotesAPI"]
```

- [ ] **Step 5: Run tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_quotes.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/fidelity_trader/market_data/ src/fidelity_trader/models/quote.py tests/test_quotes.py
git commit -m "feat: add quotes API with real-time quote retrieval"
```

---

## Task 6: Options Chain Module

**Files:**
- Create: `src/fidelity_trader/options/chains.py`
- Modify: `src/fidelity_trader/options/__init__.py`
- Create: `src/fidelity_trader/models/option.py`
- Create: `tests/test_options.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_options.py
import httpx
import respx

from fidelity_trader._http import BASE_URL
from fidelity_trader.options.chains import OptionsAPI

EXPIRATIONS_RESPONSE = {
    "expirations": [
        {"date": "03/30/2026", "daysToExpiration": "0", "optionPeriodicity": "W", "setType": "P", "key": "0|P"},
        {"date": "04/06/2026", "daysToExpiration": "7", "optionPeriodicity": "W", "setType": "P", "key": "7|P"},
    ]
}

CHAIN_RESPONSE = {
    "callsAndPuts": [
        {
            "expirationData": {"date": "03/30/2026", "daysToExpiration": "0", "settlementType": "PM"},
            "strike": "5800.00",
            "callBid": "55.20", "callAsk": "56.00", "callDelta": "0.45",
            "callGamma": "0.003", "callTheta": "-2.50", "callVega": "5.20",
            "callImpliedVolatility": "0.15", "callVolume": "1500", "callOpenInterest": "25000",
            "callSelection": "-SPXW260330C5800",
            "putBid": "5.80", "putAsk": "6.20", "putDelta": "-0.08",
            "putGamma": "0.001", "putTheta": "-1.20", "putVega": "2.10",
            "putImpliedVolatility": "0.18", "putVolume": "800", "putOpenInterest": "15000",
            "putSelection": "-SPXW260330P5800",
        },
    ]
}

@respx.mock
def test_get_expirations():
    respx.get(f"{BASE_URL}/ftgw/digital/options-research/api/option-expirations").mock(
        return_value=httpx.Response(200, json=EXPIRATIONS_RESPONSE)
    )

    client = httpx.Client()
    api = OptionsAPI(client)
    exps = api.get_expirations(".SPX")
    assert len(exps) == 2
    assert exps[0].date == "03/30/2026"
    assert exps[0].days_to_expiration == 0
    client.close()

@respx.mock
def test_get_chain():
    respx.get(f"{BASE_URL}/ftgw/digital/options-research/api/slo-chain").mock(
        return_value=httpx.Response(200, json=CHAIN_RESPONSE)
    )

    client = httpx.Client()
    api = OptionsAPI(client)
    chain = api.get_chain("SPX", expiration_dates=["03/30/2026"])
    assert len(chain) == 1
    assert chain[0].strike == 5800.0
    assert chain[0].call_delta == 0.45
    assert chain[0].put_delta == -0.08
    assert chain[0].call_symbol == "-SPXW260330C5800"
    client.close()

@respx.mock
def test_get_volatility():
    respx.get(f"{BASE_URL}/ftgw/digital/options-research/api/volatility-extended").mock(
        return_value=httpx.Response(200, json={"hv10": "12.5", "hv30": "15.0", "iv30": "18.0"})
    )

    client = httpx.Client()
    api = OptionsAPI(client)
    vol = api.get_volatility("SPX")
    assert "hv10" in vol
    client.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_options.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Option models**

```python
# src/fidelity_trader/models/option.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from fidelity_trader.models.account import _parse_float, _parse_int

class OptionExpiration(BaseModel):
    date: str
    days_to_expiration: int = Field(0, alias="daysToExpiration")
    periodicity: str = Field("", alias="optionPeriodicity")
    set_type: str = Field("", alias="setType")
    key: str = ""

    @field_validator("days_to_expiration", mode="before")
    @classmethod
    def parse_dte(cls, v):
        if isinstance(v, str):
            return int(v) if v else 0
        return v

class OptionStrike(BaseModel):
    strike: Optional[float] = None
    expiration_date: str = ""
    days_to_expiration: Optional[int] = None
    settlement_type: str = ""

    # Call side
    call_bid: Optional[float] = Field(None, alias="callBid")
    call_ask: Optional[float] = Field(None, alias="callAsk")
    call_last: Optional[float] = Field(None, alias="callLast")
    call_bid_size: Optional[int] = Field(None, alias="callBidSize")
    call_ask_size: Optional[int] = Field(None, alias="callAskSize")
    call_volume: Optional[int] = Field(None, alias="callVolume")
    call_open_interest: Optional[int] = Field(None, alias="callOpenInterest")
    call_delta: Optional[float] = Field(None, alias="callDelta")
    call_gamma: Optional[float] = Field(None, alias="callGamma")
    call_theta: Optional[float] = Field(None, alias="callTheta")
    call_vega: Optional[float] = Field(None, alias="callVega")
    call_rho: Optional[float] = Field(None, alias="callRho")
    call_iv: Optional[float] = Field(None, alias="callImpliedVolatility")
    call_symbol: str = Field("", alias="callSelection")

    # Put side
    put_bid: Optional[float] = Field(None, alias="putBid")
    put_ask: Optional[float] = Field(None, alias="putAsk")
    put_last: Optional[float] = Field(None, alias="putLast")
    put_bid_size: Optional[int] = Field(None, alias="putBidSize")
    put_ask_size: Optional[int] = Field(None, alias="putAskSize")
    put_volume: Optional[int] = Field(None, alias="putVolume")
    put_open_interest: Optional[int] = Field(None, alias="putOpenInterest")
    put_delta: Optional[float] = Field(None, alias="putDelta")
    put_gamma: Optional[float] = Field(None, alias="putGamma")
    put_theta: Optional[float] = Field(None, alias="putTheta")
    put_vega: Optional[float] = Field(None, alias="putVega")
    put_rho: Optional[float] = Field(None, alias="putRho")
    put_iv: Optional[float] = Field(None, alias="putImpliedVolatility")
    put_symbol: str = Field("", alias="putSelection")

    @field_validator(
        "strike", "call_bid", "call_ask", "call_last", "call_delta", "call_gamma",
        "call_theta", "call_vega", "call_rho", "call_iv",
        "put_bid", "put_ask", "put_last", "put_delta", "put_gamma",
        "put_theta", "put_vega", "put_rho", "put_iv",
        mode="before",
    )
    @classmethod
    def parse_floats(cls, v):
        return _parse_float(v)

    @field_validator(
        "call_bid_size", "call_ask_size", "call_volume", "call_open_interest",
        "put_bid_size", "put_ask_size", "put_volume", "put_open_interest",
        "days_to_expiration",
        mode="before",
    )
    @classmethod
    def parse_ints(cls, v):
        return _parse_int(v)

    @property
    def call_mid(self) -> Optional[float]:
        if self.call_bid is not None and self.call_ask is not None:
            return round((self.call_bid + self.call_ask) / 2, 2)
        return None

    @property
    def put_mid(self) -> Optional[float]:
        if self.put_bid is not None and self.put_ask is not None:
            return round((self.put_bid + self.put_ask) / 2, 2)
        return None
```

- [ ] **Step 4: Implement OptionsAPI**

```python
# src/fidelity_trader/options/chains.py
import httpx

from fidelity_trader._http import BASE_URL
from fidelity_trader.models.option import OptionExpiration, OptionStrike


class OptionsAPI:
    """Option chains, expirations, and volatility data."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_expirations(self, symbol: str = ".SPX") -> list[OptionExpiration]:
        """Get available option expiration dates for a symbol."""
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/options-research/api/option-expirations",
            params={"symbol": symbol},
        )
        resp.raise_for_status()
        data = resp.json()
        return [OptionExpiration.model_validate(e) for e in data.get("expirations", [])]

    def get_chain(
        self,
        symbol: str = "SPX",
        expiration_dates: list[str] = None,
        strikes: str = "All",
        settlement_types: str = "",
    ) -> list[OptionStrike]:
        """Get the full option chain with Greeks."""
        params = {
            "strikes": strikes,
            "expirationDates": ",".join(expiration_dates or []),
            "settlementTypes": settlement_types,
        }
        if symbol.upper() not in ("SPX", ".SPX"):
            params["underlying"] = symbol

        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/options-research/api/slo-chain",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

        strikes_list = []
        for row in data.get("callsAndPuts", []):
            exp_data = row.get("expirationData", {})
            strike = OptionStrike.model_validate(row)
            strike.expiration_date = exp_data.get("date", "")
            strike.settlement_type = exp_data.get("settlementType", "")
            strikes_list.append(strike)

        return strikes_list

    def get_chain_multileg(
        self,
        symbol: str = "SPX",
        strategy: str = "Spread",
        expiration: str = None,
        set_type: str = "P",
        strikes: int = 10,
    ) -> dict:
        """Get multi-leg option chain (pre-built spreads, straddles, etc.)."""
        params = {
            "strikes": strikes,
            "strategy": strategy,
            "expiration1": expiration or "",
            "setType1": set_type,
            "expiration2": "",
            "setType2": "",
        }
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/options-research/api/mlo-chain",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def get_volatility(self, symbol: str = "SPX") -> dict:
        """Get historical and implied volatility (HV10/30/60, IV30/60)."""
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/options-research/api/volatility-extended",
            params={"underlying": symbol},
        )
        resp.raise_for_status()
        return resp.json()

    def get_statistics(self, symbol: str = "SPX") -> dict:
        """Get option statistics: IV percentile, volume, OI."""
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/options-research/api/key-statistics",
            params={"underlying": symbol},
        )
        resp.raise_for_status()
        return resp.json()
```

```python
# src/fidelity_trader/options/__init__.py
from fidelity_trader.options.chains import OptionsAPI

__all__ = ["OptionsAPI"]
```

- [ ] **Step 5: Run tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_options.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/fidelity_trader/options/ src/fidelity_trader/models/option.py tests/test_options.py
git commit -m "feat: add options chain API with expirations, Greeks, and volatility"
```

---

## Task 7: Compose Everything in FidelityClient

**Files:**
- Modify: `src/fidelity_trader/client.py`
- Modify: `src/fidelity_trader/__init__.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write failing test for composed client**

```python
# tests/test_client.py
import httpx
import respx

from fidelity_trader._http import BASE_URL, AUTH_URL
from fidelity_trader import FidelityClient

@respx.mock
def test_client_login_and_get_quote(fidelity_response):
    # Mock login flow
    respx.get(f"{BASE_URL}/prgw/digital/login/atp").mock(return_value=httpx.Response(200))
    respx.delete(f"{AUTH_URL}/user/session/login").mock(return_value=httpx.Response(204))
    respx.get(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("OK"))
    )
    respx.post(f"{AUTH_URL}/user/identity/remember/username/1").mock(
        return_value=httpx.Response(200, json=fidelity_response("OK"))
    )
    respx.post(f"{AUTH_URL}/user/factor/password/authentication").mock(
        return_value=httpx.Response(200, json=fidelity_response("User Authenticated"))
    )
    respx.put(f"{AUTH_URL}/user/identity/remember/username").mock(
        return_value=httpx.Response(200, json=fidelity_response("OK"))
    )
    respx.post(f"{AUTH_URL}/user/session/login").mock(
        return_value=httpx.Response(200, json=fidelity_response("Session Created"))
    )

    # Mock quote
    respx.get(f"{BASE_URL}/ftgw/digital/options-research/api/quotes").mock(
        return_value=httpx.Response(200, json={
            "quoteResponse": [{"status": "0", "requestSymbol": ".SPX", "quoteData": {"lastPrice": "5850.25"}}]
        })
    )

    with FidelityClient() as client:
        client.login("user", "pass")
        assert client.is_authenticated
        quote = client.quotes.get_quote(".SPX")
        assert quote.last_price == 5850.25

def test_client_context_manager():
    client = FidelityClient()
    assert not client.is_authenticated
    client.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_client.py -v`
Expected: FAIL (client doesn't have `.quotes` yet)

- [ ] **Step 3: Rewrite FidelityClient to compose all modules**

```python
# src/fidelity_trader/client.py
"""Main client that composes all Fidelity API modules."""

from fidelity_trader._http import create_session, BASE_URL, AUTH_URL
from fidelity_trader.auth.session import AuthSession
from fidelity_trader.accounts.accounts import AccountsAPI
from fidelity_trader.market_data.quotes import QuotesAPI
from fidelity_trader.options.chains import OptionsAPI


class FidelityClient:
    """Unofficial Fidelity Trader+ API client.

    Usage:
        with FidelityClient() as client:
            client.login(username="...", password="...")
            quote = client.quotes.get_quote(".SPX")
            accounts = client.accounts.discover_accounts()
            chain = client.options.get_chain("SPX")
    """

    def __init__(self) -> None:
        self._http = create_session()
        self._auth = AuthSession(self._http, BASE_URL, AUTH_URL)
        self.quotes = QuotesAPI(self._http)
        self.options = OptionsAPI(self._http)
        self._accounts_api: AccountsAPI | None = None

    def login(self, username: str, password: str) -> dict:
        """Authenticate with Fidelity and establish a session."""
        result = self._auth.login(username, password)
        # Initialize accounts API with CSRF support after login
        self._accounts_api = AccountsAPI(
            self._http,
            csrf_token=self._auth.get_csrf_token() if self._auth.is_authenticated else None,
        )
        return result

    def logout(self) -> None:
        """Clear the current session."""
        self._auth.logout()

    @property
    def is_authenticated(self) -> bool:
        return self._auth.is_authenticated

    @property
    def accounts(self) -> AccountsAPI:
        """Account discovery, balances, positions. Available after login."""
        if self._accounts_api is None:
            # Create without CSRF for discovery-only use
            self._accounts_api = AccountsAPI(self._http)
        return self._accounts_api

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
```

```python
# src/fidelity_trader/__init__.py
from fidelity_trader.client import FidelityClient
from fidelity_trader.exceptions import (
    FidelityError,
    AuthenticationError,
    SessionExpiredError,
    CSRFTokenError,
    APIError,
)

__all__ = [
    "FidelityClient",
    "FidelityError",
    "AuthenticationError",
    "SessionExpiredError",
    "CSRFTokenError",
    "APIError",
]
__version__ = "0.1.0"
```

- [ ] **Step 4: Run all tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/fidelity_trader/client.py src/fidelity_trader/__init__.py tests/test_client.py
git commit -m "feat: compose all modules into FidelityClient with quotes, options, accounts"
```

---

## Task 8: Trading Rules Engine

**Files:**
- Modify: `src/fidelity_trader/trading/orders.py`
- Create: `tests/test_trading.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_trading.py
import httpx
import respx

from fidelity_trader._http import BASE_URL
from fidelity_trader.trading.orders import TradingAPI

CSRF_TOKEN = "test-csrf"

@respx.mock
def test_get_trading_rules():
    respx.get(f"{BASE_URL}/ftgw/digital/trade-options/api/rules-engine").mock(
        return_value=httpx.Response(200, json={
            "accountSeeding": {"optionLevel": 5},
            "strategiesByOptionLevel": {"5": ["BuyWrite", "IronCondor", "Spread"]},
        })
    )

    client = httpx.Client()
    api = TradingAPI(client, csrf_token=CSRF_TOKEN)
    rules = api.get_trading_rules()
    assert "accountSeeding" in rules
    client.close()

@respx.mock
def test_get_trade_config():
    respx.get(f"{BASE_URL}/ftgw/digital/trade-options/api/config").mock(
        return_value=httpx.Response(200, json={"timeInForce": ["DAY", "GTC"]})
    )

    client = httpx.Client()
    api = TradingAPI(client, csrf_token=CSRF_TOKEN)
    config = api.get_trade_config()
    assert "timeInForce" in config
    client.close()

@respx.mock
def test_autosuggest():
    respx.get(f"{BASE_URL}/ftgw/digital/trade-options/api/autosuggest").mock(
        return_value=httpx.Response(200, json={
            "suggestions": [{"symbol": "AAPL", "name": "Apple Inc."}]
        })
    )

    client = httpx.Client()
    api = TradingAPI(client, csrf_token=CSRF_TOKEN)
    results = api.autosuggest("AAP")
    assert len(results) >= 1
    client.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/test_trading.py -v`
Expected: FAIL

- [ ] **Step 3: Implement TradingAPI**

```python
# src/fidelity_trader/trading/orders.py
import httpx

from fidelity_trader._http import BASE_URL
from fidelity_trader.exceptions import APIError


class TradingAPI:
    """Trading rules, configuration, and order management.

    Order placement endpoints are placeholders — they require additional
    mitmproxy captures of the order preview/submit flow to implement.
    """

    def __init__(self, http: httpx.Client, csrf_token: str = None) -> None:
        self._http = http
        self._csrf_token = csrf_token

    def _csrf_headers(self) -> dict[str, str]:
        if not self._csrf_token:
            raise APIError("CSRF token required for trading endpoints")
        return {"X-CSRF-TOKEN": self._csrf_token}

    def get_trading_rules(self) -> dict:
        """Get account trading rules: option level, allowed strategies."""
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/trade-options/api/rules-engine",
            headers=self._csrf_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_trade_config(self) -> dict:
        """Get trade configuration: time-in-force options, order types, etc."""
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/trade-options/api/config",
            headers=self._csrf_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def autosuggest(self, query: str) -> list[dict]:
        """Search for symbols by partial name or ticker."""
        resp = self._http.get(
            f"{BASE_URL}/ftgw/digital/trade-options/api/autosuggest",
            params={"query": query},
            headers=self._csrf_headers(),
        )
        resp.raise_for_status()
        return resp.json().get("suggestions", [])

    # --- Order placement (requires additional capture work) ---
    # TODO: Capture order preview/submit/modify/cancel flows via mitmproxy
    # Expected endpoints based on fidelity-api patterns:
    #   POST /ftgw/digital/trade-options/api/order-preview
    #   POST /ftgw/digital/trade-options/api/order-submit
    #   PUT  /ftgw/digital/trade-options/api/order-modify
    #   DELETE /ftgw/digital/trade-options/api/order-cancel
    #   GET  /ftgw/digital/trade-options/api/order-status
```

```python
# src/fidelity_trader/trading/__init__.py
from fidelity_trader.trading.orders import TradingAPI

__all__ = ["TradingAPI"]
```

- [ ] **Step 4: Wire TradingAPI into FidelityClient**

Add to `src/fidelity_trader/client.py`:

```python
from fidelity_trader.trading.orders import TradingAPI

# In __init__:
self._trading_api: TradingAPI | None = None

# In login(), after accounts init:
self._trading_api = TradingAPI(
    self._http,
    csrf_token=self._auth.get_csrf_token(),
)

# Add property:
@property
def trading(self) -> TradingAPI:
    """Trading rules and order management. Available after login."""
    if self._trading_api is None:
        self._trading_api = TradingAPI(self._http)
    return self._trading_api
```

- [ ] **Step 5: Run all tests**

Run: `cd ~/fidelity-trader-sdk && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/fidelity_trader/trading/ src/fidelity_trader/client.py tests/test_trading.py
git commit -m "feat: add trading rules engine, config, and autosuggest API"
```

---

## Task 9: Update Examples and README

**Files:**
- Modify: `examples/login.py`
- Create: `examples/quotes.py`
- Create: `examples/options_chain.py`
- Create: `examples/account_info.py`
- Modify: `README.md`

- [ ] **Step 1: Write complete examples**

```python
# examples/login.py
"""Login to Fidelity and verify session."""
from fidelity_trader import FidelityClient

with FidelityClient() as client:
    client.login(username="your_username", password="your_password")
    print(f"Authenticated: {client.is_authenticated}")
```

```python
# examples/quotes.py
"""Get real-time quotes."""
from fidelity_trader import FidelityClient

with FidelityClient() as client:
    client.login(username="your_username", password="your_password")

    # Single quote
    spx = client.quotes.get_quote(".SPX")
    print(f"SPX: {spx.last_price} ({spx.net_change})")

    # Multiple quotes
    quotes = client.quotes.get_quotes([".SPX", ".VIX", "AAPL"])
    for symbol, quote in quotes.items():
        print(f"{symbol}: {quote.last_price}")
```

```python
# examples/options_chain.py
"""Get SPX option chain with Greeks."""
from fidelity_trader import FidelityClient

with FidelityClient() as client:
    client.login(username="your_username", password="your_password")

    # Get available expirations
    expirations = client.options.get_expirations(".SPX")
    print(f"Found {len(expirations)} expirations")
    for exp in expirations[:5]:
        print(f"  {exp.date} ({exp.days_to_expiration} DTE)")

    # Get 0DTE chain
    if expirations:
        chain = client.options.get_chain("SPX", [expirations[0].date])
        for strike in chain[:10]:
            print(
                f"  Strike {strike.strike}: "
                f"Call {strike.call_bid}/{strike.call_ask} d={strike.call_delta} | "
                f"Put {strike.put_bid}/{strike.put_ask} d={strike.put_delta}"
            )
```

```python
# examples/account_info.py
"""Discover accounts, balances, and positions."""
from fidelity_trader import FidelityClient

with FidelityClient() as client:
    client.login(username="your_username", password="your_password")

    # Discover accounts
    accounts = client.accounts.discover_accounts()
    for acct in accounts:
        print(f"Account: {acct.acct_num} ({acct.nickname}) - Level {acct.option_level}")

        # Get balances
        balance = client.accounts.get_balances(acct.acct_num)
        print(f"  Value: ${balance.total_account_value:,.2f}")
        print(f"  Cash:  ${balance.cash_available:,.2f}")

        # Get positions
        positions = client.accounts.get_positions(acct.acct_num)
        for pos in positions:
            print(f"  {pos.symbol}: {pos.quantity} shares @ ${pos.last_price}")
```

- [ ] **Step 2: Update README.md**

Update the status checklist and add API reference section showing all available methods:

```markdown
## Status

- [x] Authentication (login/logout)
- [x] CSRF token management
- [x] Account discovery
- [x] Account balances & buying power
- [x] Account positions
- [x] Real-time quotes (single & batch)
- [x] Option expirations
- [x] Option chains with full Greeks
- [x] Multi-leg option chains
- [x] Implied/historical volatility
- [x] Option statistics
- [x] Trading rules engine
- [x] Symbol autosuggest
- [ ] Order placement / preview / submit
- [ ] Order modification / cancellation
- [ ] Order history / status
- [ ] Watchlists
- [ ] Alerts
- [ ] Streaming data
```

- [ ] **Step 3: Commit**

```bash
git add examples/ README.md
git commit -m "docs: add usage examples for quotes, options, and accounts"
```

---

## Task 10: Update CLAUDE.md with Complete API Reference

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

Add the complete endpoint reference and module map to CLAUDE.md so future sessions have full context. Include:
- All discovered endpoints with their auth requirements (cookie-only vs CSRF)
- The module → endpoint mapping
- Known response shapes
- Outstanding capture work needed (order flow, watchlists, alerts, streaming)

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with complete API surface reference"
```

---

## Completed Tasks (from captured traffic)

| Task | Module | Endpoint | Status |
|------|--------|----------|--------|
| Shared HTTP Layer | `_http.py`, `exceptions.py` | — | DONE |
| Pydantic Models (auth) | `models/auth.py` | — | DONE |
| CSRF Token Management | `auth/session.py` | — | DONE |
| 2FA/TOTP Login | `auth/session.py` | `ecaap/user/factor/totp/authentication` | DONE |
| Credentials Providers | `credentials.py` | AWS Secrets Manager, SSM, env, file | DONE |
| Positions API | `portfolio/positions.py` | `dpservice/ftgw/dp/position/v2` | DONE |
| Balances API | `portfolio/balances.py` | `dpservice/ftgw/dp/balance/detail/v2` | DONE |
| Order Status API | `orders/status.py` | `dpservice/ftgw/dp/retail-order-status/v3/...` | DONE |
| Option Summary API | `portfolio/option_summary.py` | `dpservice/ftgw/dp/retail-am-optionsummary/...` | DONE |
| Transaction History | `portfolio/transactions.py` | `dpservice/ftgw/dp/accountmanagement/transaction/history/v2` | DONE |
| Research (Earnings/Dividends) | `research/data.py` | `dpservice/ftgw/dpdirect/research/earning+dividend/v1` | DONE |
| Streaming News Auth | `streaming/news.py` | `streaming-news.mds.fidelity.com/ftgw/snaz/Authorize` | DONE |
| FidelityClient Composition | `client.py` | — | DONE |

---

## MDDS WebSocket Streaming — Task Block

Discovered from captured traffic: Fidelity Trader+ gets ALL real-time market data through WebSocket connections to `mdds-i-tc.fidelity.com`. This is not a REST API — it's a persistent streaming protocol. See `docs/captures/2026-03-30-websocket-streaming.md` for full protocol documentation.

### Streaming Task S1: Market-Hours Capture (REQUIRES USER)

**Capture during market hours** to see real tick data flowing with bid/ask/last/volume/Greeks.
Weekend captures only show initial subscription responses, not live ticks.

- [ ] Step 1: Enable mitmproxy during market hours (Mon-Fri 9:30-16:00 ET)
- [ ] Step 2: User opens Trader+ and watches a few symbols (SPX, AAPL, etc.)
- [ ] Step 3: Capture for 2-3 minutes to collect streaming tick data
- [ ] Step 4: Run `ws_dump.py` to extract messages
- [ ] Step 5: Document all field numbers with their meanings

### Streaming Task S2: Build MDDS Field Mapping

**Files:**
- Create: `src/fidelity_trader/streaming/mdds_fields.py`
- Create: `tests/test_mdds_fields.py`

Map all numbered field IDs to human-readable names. Known so far:
```python
MDDS_FIELDS = {
    "0": "status",
    "1": "security_name",
    "10": "symbol_root",
    "11": "symbol_display",
    "12": "price_change",
    "13": "price_change_pct",
    "14": "fifty_two_week_high",
    "15": "fifty_two_week_high_date",
    "16": "fifty_two_week_low",
    "17": "fifty_two_week_low_date",
    "124": "last_price",
    "128": "security_type_code",
    "169": "data_quality",  # "realtime" or "delayed"
    # TODO: bid, ask, bid_size, ask_size, volume, open, close, Greeks...
}
```

- [ ] Step 1: Write field mapping module from market-hours capture data
- [ ] Step 2: Write tests validating field parsing
- [ ] Step 3: Commit

### Streaming Task S3: Build MDDS WebSocket Client

**Files:**
- Create: `src/fidelity_trader/streaming/mdds.py`
- Create: `tests/test_mdds.py`

Async WebSocket client using `websockets` library:

```python
class MDDSClient:
    """Real-time market data streaming via Fidelity MDDS WebSocket."""

    async def connect(self, cookies: dict) -> None:
        """Connect to mdds-i-tc.fidelity.com with session cookies."""

    async def subscribe(self, symbols: list[str], include_greeks: bool = False, conflation_ms: int = 1000) -> None:
        """Subscribe to real-time data for symbols."""

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from symbols."""

    async def stream(self) -> AsyncIterator[Quote]:
        """Yield parsed quote updates as they arrive."""

    async def close(self) -> None:
        """Disconnect."""
```

- [ ] Step 1: Write failing tests for MDDSClient (connect, subscribe, stream)
- [ ] Step 2: Implement MDDSClient with websockets library
- [ ] Step 3: Handle multi-connection architecture (split symbols across connections)
- [ ] Step 4: Parse numbered field data into pydantic Quote models using field mapping
- [ ] Step 5: Run tests, commit

### Streaming Task S4: Build Streaming Quote API

**Files:**
- Create: `src/fidelity_trader/streaming/quotes.py`
- Modify: `src/fidelity_trader/client.py` (add async streaming support)

High-level API wrapping the MDDS client:

```python
class StreamingQuotesAPI:
    """Real-time streaming quotes via MDDS WebSocket."""

    async def watch(self, symbols: list[str], include_greeks: bool = False) -> AsyncIterator[QuoteUpdate]:
        """Stream real-time quote updates for symbols."""

    async def get_snapshot(self, symbols: list[str]) -> dict[str, Quote]:
        """Subscribe, get one snapshot, unsubscribe."""
```

- [ ] Step 1: Write tests
- [ ] Step 2: Implement StreamingQuotesAPI
- [ ] Step 3: Wire into FidelityClient as `client.streaming_quotes`
- [ ] Step 4: Write example script
- [ ] Step 5: Commit

### Streaming Task S5: News WebSocket Client

**Files:**
- Create: `src/fidelity_trader/streaming/news_feed.py`

Connect to `fid-str.newsedge.net:443` using the AccessToken from the Authorize endpoint. Requires a capture of the actual news WebSocket to map the message format.

- [ ] Step 1: Capture news WebSocket traffic (user watches news in Trader+)
- [ ] Step 2: Document message format
- [ ] Step 3: Implement NewsFeedClient
- [ ] Step 4: Commit

---

## Future Tasks (require additional mitmproxy captures)

These tasks cannot be implemented until the corresponding traffic is captured from Fidelity Trader+:

### Task F1: Order Placement Flow
- Capture: Preview an order in Fidelity Trader+ with mitmproxy running (don't submit)
- Build: `TradingAPI.preview_order()`, `TradingAPI.submit_order()`

### Task F2: Order Modification & Cancellation
- Capture: Modify and cancel an open order
- Build: `TradingAPI.modify_order()`, `TradingAPI.cancel_order()`

### Task F3: Watchlists
- Capture: Create, edit, delete watchlists
- Build: `WatchlistsAPI` module

### Task F4: Alerts
- Capture: Create, manage price/volume alerts
- Build: `AlertsAPI` module

### Task F5: Options Chain Lookup
- Capture: Open an options chain in Trader+
- Build: `OptionsAPI.get_chain()`, `OptionsAPI.get_expirations()`

### Task F6: Equity Trading
- Capture: Place equity order (different from options flow)
- Build: `EquityTradingAPI`

### Task F7: Statements & Documents
- Capture: Download statements, tax documents
- Build: `DocumentsAPI` module

### Task F8: Closed Positions Detail
- Endpoint already captured: `dpservice/ftgw/dp/customer-am-position/v1/accounts/closedposition`
- Build: `PortfolioAPI.get_closed_positions()` — can implement now, just needs response analysis
