# Development

```bash
git clone https://github.com/brownjosiah/fidelity-trader-api.git
cd fidelity-trader-api
pip install -e ".[dev,cli,service]"

# Run tests
pytest                              # all 1587 tests
pytest tests/test_positions.py -v   # single module
pytest --cov=fidelity_trader        # with coverage

# Lint
ruff check src/ service/ tests/
```

## Adding New API Modules

This SDK is built from captured network traffic. The workflow:

1. Start mitmproxy: `mitmweb --listen-port 8080 -w ~/capture.flow`
2. Route Trader+ through the proxy (system proxy + CA cert)
3. Perform the target action in Trader+
4. Analyze the capture: extract endpoints, request/response shapes
5. Create Pydantic model, API module, client integration, and tests

See [`docs/BACKLOG.md`](https://github.com/brownjosiah/fidelity-trader-api/blob/main/docs/BACKLOG.md) for the full backlog.
