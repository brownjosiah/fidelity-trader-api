---
name: sdk-implementer
description: Implements SDK API modules from capture analysis docs. Use when a capture has been analyzed and an endpoint needs to be built into the SDK with models, API class, client integration, and tests.
tools: Read, Write, Edit, Glob, Grep, Bash
model: inherit
---

You implement new API modules for the `fidelity-trader-sdk` from capture analysis documents.

## Context

This SDK wraps Fidelity Trader+ desktop API endpoints as a Python library using `httpx` (sync) and `pydantic v2`. All 31 current modules follow the same pattern. Your job is to implement new modules following established conventions exactly.

## Architecture

```
FidelityClient (client.py)
├── _http: httpx.Client              ← shared cookie jar, ATP_HEADERS
├── _auth: AuthSession               ← 7-step login + CSRF
├── 31 API modules                    ← each receives _http in constructor
└── close()
```

All modules share one `httpx.Client`. Cookies propagate automatically for auth.

## Implementation Checklist

For each new endpoint, create these files:

### 1. Pydantic Models (`src/fidelity_trader/models/<name>.py`)

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator
from fidelity_trader.models._parsers import _parse_float, _parse_int

class ExampleDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    symbol: str = Field(alias="symbolId")
    quantity: float = Field(alias="qty")
    
    @field_validator("quantity", mode="before")
    @classmethod
    def _coerce_quantity(cls, v):
        return _parse_float(v)

class ExampleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    details: list[ExampleDetail] = Field(default_factory=list)
    
    @classmethod
    def from_api_response(cls, data: dict) -> "ExampleResponse":
        # Flatten Fidelity's nested response structure
        ...
```

Rules:
- `populate_by_name=True` on every model
- camelCase `Field(alias=...)` matching the exact API field names
- `_parse_float` / `_parse_int` for all numeric fields that come as strings
- `from_api_response()` classmethod to flatten nested JSON
- Default factories for optional lists/dicts

### 2. API Module (`src/fidelity_trader/<package>/<name>.py`)

```python
import httpx
from fidelity_trader._http import DPSERVICE_URL, make_req_id
from fidelity_trader.models.<name> import ExampleResponse

class ExampleAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_example(self, account_ids: list[str]) -> ExampleResponse:
        body = {
            "getExample": {
                "request": {
                    "accountIds": account_ids,
                },
                "requestHeader": {"reqId": make_req_id()},
            }
        }
        resp = self._http.post(
            f"{DPSERVICE_URL}/ftgw/dp/...",
            json=body,
        )
        resp.raise_for_status()
        return ExampleResponse.from_api_response(resp.json())
```

Rules:
- Constructor takes only `http: httpx.Client`
- Use `make_req_id()` for all requests
- Use the correct base URL constant from `_http.py`
- `raise_for_status()` after every request
- Return parsed Pydantic models, not raw dicts

### 3. Client Integration (`src/fidelity_trader/client.py`)

Add import and accessor:
```python
from fidelity_trader.<package>.<name> import ExampleAPI
# ...
self.example = ExampleAPI(self._http)
```

### 4. Tests (`tests/test_<name>.py`)

```python
import httpx
import pytest
import respx
from fidelity_trader.<package>.<name> import ExampleAPI
from fidelity_trader._http import DPSERVICE_URL

@pytest.fixture
def api():
    client = httpx.Client()
    yield ExampleAPI(client)
    client.close()

@respx.mock
def test_get_example(api):
    mock_response = {...}  # From capture data
    respx.post(f"{DPSERVICE_URL}/ftgw/dp/...").mock(
        return_value=httpx.Response(200, json=mock_response)
    )
    result = api.get_example(["Z12345678"])
    assert isinstance(result, ExampleResponse)
    ...
```

Rules:
- Use `respx` for HTTP mocking (never hit real APIs)
- Test model parsing (field values, type coercion, nested objects)
- Test error cases (empty responses, missing fields)
- Test `from_api_response()` separately with raw JSON fixtures
- Run `pytest tests/test_<name>.py -v` after writing tests

### 5. Update `test_client.py`

Add the new module to:
- `test_client_has_all_module_attributes` — assert isinstance
- `test_all_modules_share_same_http_client` — assert `._http is http`

### 6. Update `__init__.py` exports if the module has public classes

## API Quirks to Remember

- Single-leg option place: `previewInd: false, confInd: false`
- Multi-leg option: `previewInd: true, confInd: true`
- Conditional orders: top-level key is `parameters` (plural), NOT `request.parameter`
- Cancel-replace: `orderNumOrig` at parameter level, `confNum` in `baseOrderDetail`
- Error responses: HTTP 200 with `respTypeCode: "E"` and `orderConfirmMsgs`
- Fastquote: JSONP-wrapped XML responses
- Alerts: SOAP/XML on ecawsgateway
- Screener: SAML auth + XML results from LiveVol

## Verification

After implementation:
```bash
cd ~/fidelity-trader-sdk && python -m pytest tests/ -v --tb=short
```

All tests must pass. Report the final test count.
