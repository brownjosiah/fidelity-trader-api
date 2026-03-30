# fidelity-trader-sdk

Unofficial Python SDK for the Fidelity Trader+ API.

## Install

```bash
pip install -e ".[dev]"
```

## Usage

```python
from fidelity_trader import FidelityClient

with FidelityClient() as client:
    client.login(username="your_username", password="your_password")
    # authenticated — make API calls
```

## Status

- [x] Authentication (login/logout)
- [ ] Portfolio (positions, balances)
- [ ] Trading (orders)
- [ ] Market Data (quotes)
