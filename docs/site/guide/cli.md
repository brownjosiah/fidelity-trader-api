# CLI Reference

The `ft` command-line tool provides 17 commands for interacting with your Fidelity account.

## Authentication

```bash
ft login                          # Interactive login (prompts or reads env vars)
ft login --username X --password Y  # Non-interactive
ft logout                         # Clear saved session
ft status                         # Check session health
```

Sessions are saved to `~/.config/ft/session.json` (Linux/Mac) or `%APPDATA%/ft/session.json` (Windows) and persist across commands. Sessions expire after ~30 minutes of inactivity.

## Portfolio

```bash
ft accounts                       # List all accounts
ft positions                      # Positions (auto-selects account if only one)
ft positions Z12345678             # Positions for specific account
ft balances                       # Account balances
```

## Trading

```bash
# Equity orders (preview by default)
ft buy AAPL 10                    # Market buy — preview only
ft buy AAPL 10 --limit 150.00    # Limit buy — preview only
ft sell TSLA 5 --stop 200.00     # Stop sell — preview only
ft buy AAPL 10 --limit 150 --live  # Actually place the order
ft buy AAPL 10 --limit 150 --live --yes  # Skip confirmation prompt

# Order management
ft orders                         # List open/recent orders
ft cancel CONF123                 # Cancel an order (always works, not gated)

# Options
ft options chain AAPL             # Option chain
ft options buy AAPL250418C00170000 1 --limit 3.50  # Buy call — preview
ft options sell AAPL250418P00160000 1 --live        # Sell put — live
```

## Market Data & Research

```bash
ft quote AAPL TSLA NVDA           # Quick quotes
ft chart AAPL --bars D --days 30  # Historical OHLCV
ft search "apple"                 # Symbol search
ft earnings AAPL MSFT             # Earnings data
ft dividends KO PG               # Dividend data
```

## Streaming

```bash
ft stream AAPL TSLA               # Live streaming quotes (updates in-place)
ft stream AAPL --fields last,bid,ask,volume  # Custom fields
```

## Output Formats

All commands support `--format json` for piping:

```bash
ft positions --format json | jq '.[] | select(.symbol == "AAPL")'
ft quote AAPL --format json
```
