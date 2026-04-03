"""Root Typer application for the ft CLI."""

from __future__ import annotations

from typing import Optional

import typer

from fidelity_trader.cli._auth import login, logout, status
from fidelity_trader.cli._market_data import quote, chart, search
from fidelity_trader.cli._options import options_app
from fidelity_trader.cli._orders import orders, buy, sell, cancel
from fidelity_trader.cli._portfolio import accounts, positions, balances
from fidelity_trader.cli._research import earnings, dividends
from fidelity_trader.cli._stream import stream

app = typer.Typer(
    name="ft",
    help="Fidelity Trader+ CLI -- Your Fidelity account, your API.",
    no_args_is_help=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    format: str = typer.Option("table", "--format", "-f", help="Output format: table or json"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account number"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Fidelity Trader+ CLI -- Your Fidelity account, your API."""
    ctx.ensure_object(dict)
    ctx.obj["format"] = format
    ctx.obj["account"] = account
    ctx.obj["verbose"] = verbose


# Register auth commands at top level (ft login, ft logout, ft status)
app.command("login")(login)
app.command("logout")(logout)
app.command("status")(status)

# Register portfolio commands at top level (ft accounts, ft positions, ft balances)
app.command("accounts")(accounts)
app.command("positions")(positions)
app.command("balances")(balances)

# Register order commands at top level (ft orders, ft buy, ft sell, ft cancel)
app.command("orders")(orders)
app.command("buy")(buy)
app.command("sell")(sell)
app.command("cancel")(cancel)

# Register options subcommand group (ft options chain, ft options buy, ft options sell)
app.add_typer(options_app)

# Register market data commands at top level (ft quote, ft chart, ft search)
app.command("quote")(quote)
app.command("chart")(chart)
app.command("search")(search)

# Register research commands at top level (ft earnings, ft dividends)
app.command("earnings")(earnings)
app.command("dividends")(dividends)

# Register streaming command at top level (ft stream)
app.command("stream")(stream)
