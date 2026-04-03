# Fidelity Trader API

**Your Fidelity account, your API.**

Unofficial Python SDK, CLI, and self-hosted REST service for the Fidelity Trader+ API. Built by reverse-engineering network traffic from the Fidelity Trader+ desktop application via mitmproxy captures.

!!! warning "Disclaimer"
    This is an unofficial, community-driven project. It is not affiliated with, endorsed by, or supported by Fidelity Investments. Use at your own risk. Trading involves risk of financial loss. By using this software, you accept full responsibility for any trades placed through your account.

## Features

- **31 API modules** covering portfolio, trading, market data, research, streaming, alerts, and more
- **CLI tool (`ft`)** with 17 commands — positions, trading, quotes, streaming, all from your terminal
- **Self-hosted REST service** — 57 endpoints via FastAPI, Docker-ready, language-agnostic
- **Dry-run safety** — order placement defaults to preview-only; live trading requires explicit opt-in
- **Real-time WebSocket streaming** via Fidelity's MDDS protocol (live quotes, options with Greeks, 25-level L2 depth)
- **Full order lifecycle** — preview, place, cancel, and modify equity, single-leg option, multi-leg option, and conditional orders
- **Pydantic v2 models** for all API responses with type-safe field access
- **Credential providers** — AWS Secrets Manager, SSM Parameter Store, environment variables
- **Async client** via `AsyncFidelityClient` (wraps sync SDK with `asyncio.to_thread`)
- **Retry transport** with exponential backoff for transient failures
- **Auto session refresh** — background keep-alive for long-running applications
- **1587 tests** with full HTTP mocking via respx

## Get Started

```bash
pip install fidelity-trader-api[cli]
```

Head to the [Installation](getting-started/installation.md) page for extras and requirements, or jump straight to the [Quick Start](getting-started/quickstart.md) to start using the SDK, CLI, or REST service.
