# Project Decisions Log

> Decided: 2026-04-02

---

## Naming & Identity

| # | Decision | Choice | Notes |
|---|----------|--------|-------|
| 1 | Package name | `fidelity-trader-api` | PyPI name. Python import stays `fidelity_trader` (no code refactor needed). |
| 2 | GitHub repo name | `fidelity-trader-api` | Match package name. |
| 3 | CLI command name | `ft` | Short, fast to type. `ft login`, `ft positions`, `ft buy`. |

## Project Structure

| # | Decision | Choice | Notes |
|---|----------|--------|-------|
| 4 | Repo structure | Mono-repo | SDK + service + CLI all in one repo. |
| 5 | Service directory | `service/` (top-level) | Separate deployable, imports SDK as dependency. CLI lives in `src/fidelity_trader/cli/` since it ships with the SDK package. |

```
fidelity-trader-api/
├── src/fidelity_trader/       # SDK library (pip install)
│   ├── cli/                   # CLI tool (ft command)
│   └── ...                    # 31 API modules
├── service/                   # FastAPI service (separate deployable)
│   ├── routes/
│   ├── session/
│   ├── streaming/
│   └── ...
├── docker/                    # Docker packaging
├── tests/                     # All tests (SDK + service + CLI)
├── docs/                      # Documentation
└── pyproject.toml             # Single package, extras for service
```

## Release Strategy

| # | Decision | Choice | Notes |
|---|----------|--------|-------|
| 6 | MVP release scope | SDK + CLI + Service | Full stack in first public release. |
| 7 | Go-public timing | When complete + internally tested | No fixed date. Release when Josiah finishes internal testing. |
| 8 | Versioning | SemVer with codified rules | See [Versioning Convention](#versioning-convention) below. |

## Safety & Legal

| # | Decision | Choice | Notes |
|---|----------|--------|-------|
| 9 | Default mode | Dry-run (preview-only) | Placing orders requires explicit opt-in via `--live` flag (CLI) or `FIDELITY_LIVE_TRADING=true` env var (SDK/service). |
| 10 | Order guardrails | None (user's responsibility) | No built-in position limits or size caps. |
| 11 | License | Apache 2.0 | |
| 12 | Takedown plan | None | No mirror. Comply if asked. |

## Security

| # | Decision | Choice | Notes |
|---|----------|--------|-------|
| 13 | Credential storage | Env vars + cloud integrations | Primary: env vars (`FIDELITY_USERNAME`, `FIDELITY_PASSWORD`, `FIDELITY_TOTP_SECRET`). Integrations: AWS Secrets Manager, AWS SSM Parameter Store (already implemented). Backlog: HashiCorp Vault, Azure Key Vault. |
| 14 | Logging policy | Don't log request/response bodies | No special filtering — just never log bodies. They contain account numbers, balances, positions. |

## Infrastructure & Community

| # | Decision | Choice | Notes |
|---|----------|--------|-------|
| 15 | Docs hosting | GitHub Pages | MkDocs Material deployed via GitHub Actions. |
| 16 | Community platform | None at launch | Revisit after traction. |
| 17 | CI integration testing | Real Fidelity account | Josiah will provide credentials for smoke tests. Secrets stored in GitHub Actions. |
| 18 | Docker registry | GHCR + Docker Hub | Publish to both on release. |

## Scope Boundaries

| # | Decision | Choice | Notes |
|---|----------|--------|-------|
| 19 | OpenAPI spec | Auto-generated as-is | Polish later once service is stable. |
| 20 | Generated client libraries | Backlogged | Official TS and Go clients planned for later. |
| 21 | Webhook/callback system | Phase 3 | Not in MVP. |
| 22 | Contribution model | Closed initially | Write contribution guide later. All implementation must come from mitmproxy captures (no guessing). |

---

## Versioning Convention

SemVer (`MAJOR.MINOR.PATCH`) with these rules:

### When to bump MAJOR (breaking)
- Removing or renaming a public SDK class, method, or property
- Changing method signatures in a backwards-incompatible way
- Changing the service REST API in a backwards-incompatible way (removing endpoints, changing response shapes)
- Changing CLI command names or required argument positions
- Dropping support for a Python version

### When to bump MINOR (feature)
- Adding a new SDK API module (e.g., new Fidelity endpoint)
- Adding a new CLI command
- Adding a new service REST endpoint
- Adding a new credential provider integration
- Adding new fields to existing Pydantic models (non-breaking)
- Adding new optional parameters to existing methods

### When to bump PATCH (fix)
- Bug fixes in existing modules
- Test improvements or additions
- Documentation changes
- Dependency updates (non-breaking)
- Performance improvements
- Internal refactoring with no public API change

### Pre-1.0 rules
- While on `0.x.y`, MINOR bumps may include breaking changes (standard SemVer pre-1.0 convention)
- Target `1.0.0` for first public release after internal testing is complete

### Version locations
- `pyproject.toml` → `version = "X.Y.Z"` (source of truth)
- `src/fidelity_trader/__init__.py` → `__version__ = "X.Y.Z"` (runtime access)
- Both must be updated together on every version bump
- Git tag: `vX.Y.Z` (triggers PyPI publish + Docker build via GitHub Actions)

---

## Dry-Run Mode Specification

### SDK behavior
- New module-level or client-level setting: `live_trading`
- Default: `False`
- When `False`: `preview_*` methods work normally, `place_*` methods raise `DryRunError` with the preview result
- When `True`: all methods work normally
- Set via: `FidelityClient(live_trading=True)` or `FIDELITY_LIVE_TRADING=true` env var

### CLI behavior
- All read operations work normally (positions, balances, quotes, etc.)
- Order commands default to preview-only
- `--live` flag required to actually place: `ft buy AAPL 10 --limit 150 --live`
- Without `--live`, prints preview result and exits with message: "Dry-run mode. Add --live to place this order."

### Service behavior
- Config setting: `FTSERVICE_LIVE_TRADING=false` (default)
- Preview endpoints always work
- Place endpoints return 403 with `LIVE_TRADING_DISABLED` error code when dry-run is active
- Status endpoint (`GET /auth/status`) includes `live_trading: true/false` in response

---

## Backlog Items Added From Decisions

| Item | Priority | Source |
|------|----------|--------|
| CLI tool (`ft` command) | **High** | Decision #3, #6 |
| Dry-run mode for SDK/CLI/service | **High** | Decision #9 |
| Rename package to `fidelity-trader-api` in pyproject.toml | **High** | Decision #1 |
| Update license to Apache 2.0 | **High** | Decision #11 |
| GitHub Pages docs site (MkDocs) | Medium | Decision #15 |
| CI smoke tests with real account | Medium | Decision #17 |
| Docker Hub publishing workflow | Medium | Decision #18 |
| HashiCorp Vault credential provider | Low | Decision #13 |
| Azure Key Vault credential provider | Low | Decision #13 |
| Official TypeScript client (from OpenAPI) | Low | Decision #20 |
| Official Go client (from OpenAPI) | Low | Decision #20 |
| Contribution guide | Low | Decision #22 |
