# Safety: Dry-Run Mode

!!! danger "Orders are blocked by default"
    All order placement is blocked by default. This prevents accidental trades when developing or testing.

| Context | Default | How to enable live trading |
|---------|---------|---------------------------|
| **SDK** | `live_trading=False` | `FidelityClient(live_trading=True)` or `FIDELITY_LIVE_TRADING=true` env var |
| **CLI** | Preview-only | Add `--live` flag: `ft buy AAPL 10 --limit 150 --live` |
| **Service** | Preview-only | Set `FTSERVICE_LIVE_TRADING=true` env var |

In dry-run mode:

- `preview_*` methods work normally
- `place_*` methods raise `DryRunError`
- The CLI shows the preview result and prints "Dry-run mode. Add --live to place this order."
- Cancellation is never blocked (you can always cancel orders)
