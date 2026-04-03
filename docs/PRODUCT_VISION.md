# Fidelity Trader — Product Vision & Strategy

> Last updated: 2026-04-02

---

## Core Value Proposition

**"Your Fidelity account, your API."**

Fidelity has no public API for retail traders. Interactive Brokers, Alpaca, Schwab (via the old TDA API) — they all have official APIs. Fidelity doesn't. This project is **the missing API layer** that gives people programmatic access to their own brokerage accounts.

Every other major brokerage offers developers a way to build on top of their platform. Fidelity, despite being the largest retail broker in the US, forces users into their desktop app or website with no programmatic alternative. This project changes that — built entirely by reverse-engineering the Fidelity Trader+ desktop application's actual network calls via mitmproxy captures.

---

## Target Audiences

There are distinct audiences with different needs. The project should be layered to serve each of them:

| Audience | What they want | Technical level | Delivery layer |
|----------|---------------|-----------------|----------------|
| **Python algo traders** | `pip install`, call methods, build strategies | High — they'll read docs, write code | SDK (Layer 1) |
| **Polyglot developers** | REST API they can hit from JS/Go/Rust/whatever | High — but not necessarily Python | Service + OpenAPI (Layers 2-3) |
| **Scripters / CLI users** | `ftcli positions` or `ftcli buy AAPL 10 --limit 150` | Medium — comfortable in a terminal | CLI (Layer 4) |
| **Tinkerers / dashboard builders** | Local API they can wire Grafana, n8n, Home Assistant to | Medium — can follow a Docker tutorial | Service + Docker (Layer 2) |
| **Non-technical traders** | "I want alerts/automation but Fidelity's tools aren't enough" | Low — need a GUI or managed solution | Out of scope (product company territory, not OSS) |

The first four are realistic open-source targets. The fifth requires a product company, not an open-source project.

---

## Deliverable Stack

The project delivers four layers, each building on the one below:

```
┌─────────────────────────────────────────────┐
│  Layer 4: CLI Tool (ftcli)                  │  Terminal users, shell scripts
│  ftcli login / positions / buy / alerts     │  cron jobs, piping to jq
├─────────────────────────────────────────────┤
│  Layer 3: OpenAPI Spec (auto-generated)     │  Client generation for any language
│  TypeScript, Go, Rust, Java clients         │  FastAPI gives this nearly free
├─────────────────────────────────────────────┤
│  Layer 2: Self-Hosted REST Service          │  Language-agnostic access
│  docker run → localhost:8787/api/v1/...     │  Session mgmt, streaming fan-out
├─────────────────────────────────────────────┤
│  Layer 1: Python SDK (fidelity-trader)      │  The foundation — all protocol logic
│  pip install fidelity-trader                │  31 modules, models, auth, streaming
└─────────────────────────────────────────────┘
```

### Layer 1: Python SDK (COMPLETE)

The foundation. All Fidelity protocol logic lives here. 31 API modules, pydantic v2 models, cookie-based auth with 7-step login handshake, MDDS WebSocket streaming with L2 depth, and 1400+ tests.

- **Package:** `fidelity-trader` on PyPI
- **Install:** `pip install fidelity-trader`
- **Audience:** Python developers building trading bots, portfolio tools, data pipelines

### Layer 2: Self-Hosted REST Service (PLANNED)

A FastAPI wrapper around the SDK that exposes all 31 modules as REST endpoints. Adds session lifecycle management, credential storage, streaming fan-out via SSE/WebSocket, and Docker deployment. Detailed plan in [`SERVICE_PLAN.md`](SERVICE_PLAN.md).

- **Package:** `fidelity-trader[service]` (extras install)
- **Deploy:** `docker run` or `docker compose up`
- **Audience:** Developers in any language, tinkerers wiring tools together

### Layer 3: OpenAPI Spec (FREE WITH LAYER 2)

FastAPI auto-generates an OpenAPI spec. If intentionally polished (good descriptions, examples, proper schema names), people can auto-generate typed clients in any language. Publish the spec, someone runs `openapi-generator` and has a Go or TypeScript client in minutes.

- **Artifact:** `openapi.json` published with each release
- **Audience:** Polyglot developers who want typed clients without writing them

### Layer 4: CLI Tool (PLANNED)

The single highest-leverage addition for open-source traction. Most people's first interaction with a project is trying it. A CLI lets someone go from `pip install` to seeing their own positions in 30 seconds:

```bash
pip install fidelity-trader
ftcli login
ftcli positions
ftcli buy AAPL 10 --type limit --price 150
ftcli stream AAPL TSLA --format json
```

Built on top of the SDK (not the service), using `typer` or `click`. Costs relatively little to build and dramatically lowers the barrier to entry. Designed for piping — `ftcli positions --format json | jq '.[] | select(.symbol == "AAPL")'`.

- **Package:** Bundled in `fidelity-trader` (CLI extras)
- **Audience:** Terminal users, scripters, cron jobs

---

## What's Missing From the Current Plan

The SERVICE_PLAN.md covers Layer 2 well. Three things it doesn't address that would significantly increase adoption:

### 1. CLI Tool

As described in Layer 4 above. This is the fastest path to "try it and see it work." Every successful API project has a CLI companion (AWS CLI, GitHub CLI, Stripe CLI). It's also the easiest way for people to debug auth issues — `ftcli login --debug` is a lot more approachable than writing a Python script.

### 2. OpenAPI Spec as a First-Class Artifact

FastAPI auto-generates OpenAPI, but the default output is messy. If we intentionally polish it:
- Proper schema names (not `Body_get_positions_accounts__acct__positions_get`)
- Request/response examples with realistic data
- Grouped by domain (portfolio, orders, market data)
- Published alongside each release

Then people can auto-generate typed clients in any language without us writing them. The community writes a Go client, a Rust client, a TypeScript client — all from the same spec.

### 3. Safety Guardrails

This is people's actual money. Before open-sourcing something that can place trades programmatically, the project needs:

- **Paper trading / dry-run mode** — Preview-only mode that never places orders. Default for new installs.
- **Configurable position limits** — Max order size, max position value, symbol allowlist/denylist
- **Explicit confirmation flows** — CLI requires `--confirm` flag for order placement, service requires preview before place
- **Order audit log** — Every order previewed/placed is logged locally with timestamp, details, result
- **Clear disclaimers** — In README, CLI output, service startup, and API responses

---

## Practical Considerations

### Naming & Branding

`fidelity-trader-sdk` is descriptive but long. For a multi-layer project, a shorter umbrella name works better:

| Option | Pros | Cons |
|--------|------|------|
| `fidelity-trader` | Descriptive, clear | Long, generic |
| `openfi` | Short, memorable, implies "open Fidelity" | Less discoverable |
| `fidapi` | Short, clear purpose | Sounds like an acronym |
| `unfidelity` | Memorable, "un-official Fidelity" | Could be seen as negative |

Current recommendation: **`fidelity-trader`** as the PyPI package name. It's what people will search for. The GitHub repo can stay `fidelity-trader-sdk` or simplify to `fidelity-trader`.

### Legal

This reverse-engineers a private API. Similar projects existed for years without issue:
- `robin_stocks` (Robinhood) — active since 2018, still maintained
- `tda-api` (TD Ameritrade) — hugely popular until Schwab merger killed the API
- Various Fidelity Selenium automation projects — still on GitHub

Legal protections needed:
- **License:** MIT or Apache 2.0 (standard for OSS tools)
- **Disclaimer:** "Unofficial, not affiliated with Fidelity Investments. Use at your own risk."
- **ToS acknowledgment:** Users are responsible for compliance with Fidelity's Terms of Service
- **No warranty:** Explicitly disclaim liability for financial losses
- **DMCA/takedown readiness:** If Fidelity sends a takedown, comply gracefully. Have the code mirrored.

### Security

People will store their brokerage credentials in whatever we build. Security posture must be:

- **Never log request/response bodies** — They contain account numbers, balances, positions
- **Encrypted credential storage** — Fernet encryption in the service, keyring/env vars for SDK/CLI
- **No telemetry** — Zero phone-home, zero analytics, zero tracking
- **Credential scoping** — Document that Fidelity credentials give FULL account access (there's no OAuth scope limiting)
- **Push env vars / secret managers** — Docs should strongly favor environment variables and secret managers over any file-based credential storage
- **Security audit before v1.0** — Community review of auth flow, credential handling, session management

### Maintenance & Sustainability

When Fidelity updates their app, endpoints can change. The capture-driven workflow is smart here:

- **Documented capture process** — The README/contributing guide should explain HOW to capture so contributors can help when things break
- **Version pinning** — Track which Fidelity Trader+ version (e.g., 4.4.1.7) each capture came from
- **Breakage detection** — CI job that tests against a known-good session (optional, requires a real account)
- **Community contribution model:**
  - Capture contributors: People who run mitmproxy and submit new endpoint data
  - Module contributors: People who implement SDK modules from capture docs
  - Service contributors: People who build service/CLI features
  - All contributions must include capture evidence (no guessing at APIs)

### Community & Adoption

What drives adoption for projects like this:

1. **"Works in 60 seconds"** — README quickstart that gets someone from zero to seeing their positions
2. **Excellent docs** — Not just API reference, but guides: "Build your first trading bot", "Set up alerts", "Stream live quotes"
3. **Discord/community** — Where people share strategies, report breakages, help each other
4. **Example projects** — A portfolio dashboard, a DCA bot, a rebalancing tool
5. **Stability** — People will not use this for real money if it breaks often

---

## Release Roadmap

### Phase 1 Release: SDK + CLI (MVP)

The minimum viable open-source release. Gets the project in front of people.

| Component | Status | Notes |
|-----------|--------|-------|
| Python SDK on PyPI | Ready | 31 modules, 1400+ tests |
| CLI tool (`ftcli`) | TODO | login, positions, balances, orders, stream |
| README with quickstart | Ready (needs CLI section) | "Your first trade in 60 seconds" |
| Security disclaimers | Partial | Need ToS, liability, credential warnings |
| Paper trading / dry-run mode | TODO | Default for new installs |
| Examples directory | Partial | full_walkthrough.py exists, need focused examples |
| PyPI publishing | Ready | GitHub Actions workflow exists |

**Release criteria:** Someone can `pip install fidelity-trader`, run `ftcli login`, see their positions, and preview (not place) an order — all within 5 minutes of finding the repo.

### Phase 2 Release: Self-Hosted Service

Unlocks the non-Python audience.

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI REST service | TODO | SERVICE_PLAN.md Phase 1-2 |
| Docker image on GHCR | TODO | SERVICE_PLAN.md Phase 5 |
| OpenAPI spec published | TODO | Auto-generated, polished |
| Streaming (SSE/WebSocket) | TODO | SERVICE_PLAN.md Phase 3 |
| Session auto-management | TODO | SERVICE_PLAN.md Phase 4 |
| Docs site (MkDocs) | TODO | API reference + guides |

**Release criteria:** Someone can `docker run` the service, authenticate via REST, and query their portfolio from any language using the published OpenAPI spec.

### Phase 3 Release: Ecosystem

Community growth and advanced features.

| Component | Status | Notes |
|-----------|--------|-------|
| Webhook/callback support | TODO | POST to URL on order fill, price trigger |
| Community contribution guide | TODO | How to capture, implement, test |
| Example projects | TODO | Dashboard, DCA bot, rebalancer |
| Generated client libraries | TODO | TypeScript, Go (from OpenAPI spec) |
| Docs site with guides | TODO | "Build your first bot", "Stream live quotes" |

**Release criteria:** Active community contributions, multiple language clients available, people running it in production for real trading.

---

## Success Metrics

How we'll know the project is succeeding:

- **GitHub stars** — Awareness (target: 500 in first 6 months)
- **PyPI downloads** — Actual usage (target: 1,000/month)
- **Docker pulls** — Service adoption
- **GitHub issues** — Community engagement (breakage reports mean people are using it)
- **Contributors** — Community health (target: 5+ contributors in first year)
- **Forks** — People building on top of it

---

## Open Questions

1. **Naming decision** — Stick with `fidelity-trader-sdk` or simplify to `fidelity-trader`?
2. **Mono-repo vs multi-repo** — Keep SDK + service + CLI in one repo, or split?
3. **Fidelity account for CI** — Do we want automated integration tests against a real account?
4. **Docs hosting** — GitHub Pages (free) or ReadTheDocs or custom?
5. **Community platform** — Discord, GitHub Discussions, or both?
6. **When to go public** — MVP first release target date?
