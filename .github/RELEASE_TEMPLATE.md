# Release Notes Template

Use this as a starting point when creating a new release via `gh release create`.

---

## Downloads

| Artifact | Description |
|----------|-------------|
| `ft-linux-amd64` | Standalone CLI binary for Linux (no Python required) |
| `ft-macos-amd64` | Standalone CLI binary for macOS (no Python required) |
| `ft-windows-amd64.exe` | Standalone CLI binary for Windows (no Python required) |
| `openapi.json` | OpenAPI 3.1 spec for TypeScript client generation |
| `openapi-3.0.json` | OpenAPI 3.0.3 spec for Go/Java/C# client generation |
| `fidelity-trader-api-go-client.tar.gz` | Pre-generated Go client (types + HTTP client) |
| `fidelity-trader-api-ts-client.tar.gz` | Pre-generated TypeScript type definitions |

## Usage

- **Python SDK:** `pip install fidelity-trader-api`
- **CLI tool:** `pip install fidelity-trader-api[cli]` or download a standalone binary above
- **REST service:** `pip install fidelity-trader-api[service]` or `docker pull ghcr.io/brownjosiah/fidelity-trader-api`
- **Go/TypeScript clients:** Download from assets above or see [Client Generation guide](https://brownjosiah.github.io/fidelity-trader-api/guide/client-generation/)

## Documentation

- [Full Documentation](https://brownjosiah.github.io/fidelity-trader-api/)
- [Installation](https://brownjosiah.github.io/fidelity-trader-api/getting-started/installation/)
- [CLI Reference](https://brownjosiah.github.io/fidelity-trader-api/guide/cli/)
- [SDK Reference](https://brownjosiah.github.io/fidelity-trader-api/guide/sdk/)
- [REST Service](https://brownjosiah.github.io/fidelity-trader-api/guide/service/)
- [Client Generation](https://brownjosiah.github.io/fidelity-trader-api/guide/client-generation/)
