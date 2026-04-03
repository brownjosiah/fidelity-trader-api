"""Option commands: options chain, options buy, options sell."""

from __future__ import annotations

from typing import Optional

import typer

from fidelity_trader.cli._errors import handle_errors
from fidelity_trader.cli._output import print_error, print_json, print_success, print_table
from fidelity_trader.cli._session import get_client, resolve_account
from fidelity_trader.models.single_option_order import SingleOptionOrderRequest

options_app = typer.Typer(name="options", help="Option chain and single-leg option orders.")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIF_MAP = {"day": "D", "gtc": "G"}
_PRICE_DESC = {"M": "Market", "L": "Limit"}


def _derive_action_code(action: str, option_symbol: str) -> str:
    """Derive the Fidelity orderActionCode from the CLI action and the option symbol.

    Option symbols follow the OCC format:  AAPL250418C00170000
    Structure: ROOT (1-6 alpha) + YYMMDD (6 digits) + C/P (1 char) + strike (8 digits)

    action: 'buy' or 'sell'
    Returns: 'BC', 'BP', 'SC', or 'SP'
    """
    # Walk past the alphabetic root, then past the 6-digit date, then the
    # next character is C or P.
    cp = "C"  # default
    i = 0
    # Skip root symbol (alphabetic characters, possibly with leading '-')
    if i < len(option_symbol) and option_symbol[i] == "-":
        i += 1
    while i < len(option_symbol) and option_symbol[i].isalpha():
        i += 1
    # Skip 6-digit date (YYMMDD)
    date_start = i
    while i < len(option_symbol) and option_symbol[i].isdigit():
        i += 1
    # The next character should be C or P
    if i < len(option_symbol) and option_symbol[i] in ("C", "P"):
        cp = option_symbol[i]

    prefix = "B" if action == "buy" else "S"
    return prefix + cp


def _display_option_preview(preview, order: SingleOptionOrderRequest) -> None:
    """Print a formatted preview summary for a single-leg option order."""
    confirm = preview.order_confirm_detail
    action_desc = {
        "BC": "Buy Call",
        "BP": "Buy Put",
        "SC": "Sell Call",
        "SP": "Sell Put",
    }.get(order.order_action_code, order.order_action_code)

    price_desc = _PRICE_DESC.get(order.price_type_code, order.price_type_code)

    price_str = "Market"
    if order.price_type_code == "L" and order.limit_price is not None:
        price_str = f"${order.limit_price:,.2f}"

    est_cost = None
    commission = None
    if confirm:
        est_cost = confirm.net_amount
        if confirm.est_commission_detail:
            commission = confirm.est_commission_detail.est_commission

    rows = [
        {"field": "Action", "value": action_desc},
        {"field": "Symbol", "value": order.symbol},
        {"field": "Contracts", "value": str(order.qty)},
        {"field": "Order Type", "value": price_desc},
        {"field": "Price", "value": price_str},
        {"field": "Time in Force", "value": "Day" if order.tif_code == "D" else "GTC"},
        {"field": "Est. Cost", "value": f"${est_cost:,.2f}" if est_cost is not None else "--"},
        {"field": "Commission", "value": f"${commission:,.2f}" if commission is not None else "$0.00"},
    ]

    print_table(
        rows=rows,
        columns=[
            {"header": "Field", "key": "field"},
            {"header": "Value", "key": "value"},
        ],
        title="Option Order Preview",
    )


def _option_order(
    ctx: typer.Context,
    action: str,
    symbol: str,
    qty: int,
    limit: float | None,
    tif: str,
    account: str | None,
    live: bool,
    yes: bool,
) -> None:
    """Shared logic for options buy/sell commands."""
    account_flag = ctx.obj.get("account") if ctx.obj else None
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    tif_code = _TIF_MAP.get(tif, "D")
    action_code = _derive_action_code(action, symbol.upper())

    price_type_code = "L" if limit is not None else "M"

    with get_client(live_trading=True) as client:
        acct_num = account or resolve_account(client, account_flag)

        order = SingleOptionOrderRequest(
            acct_num=acct_num,
            symbol=symbol.upper(),
            order_action_code=action_code,
            qty=qty,
            price_type_code=price_type_code,
            limit_price=limit,
            tif_code=tif_code,
        )

        # Step 1: Always preview first
        preview = client.single_option_orders.preview_order(order)

        if fmt == "json":
            preview_data = preview.model_dump(by_alias=True)
            preview_data["_dry_run"] = not live
            print_json(preview_data)
            if not live:
                return
        else:
            _display_option_preview(preview, order)

        # Step 2: Dry-run gate
        if not live:
            print_success("Dry-run mode. Add --live to place this order.")
            return

        # Step 3: Confirmation prompt
        if not yes:
            confirm = typer.confirm("Place this order?", default=False)
            if not confirm:
                print_success("Order cancelled.")
                return

        # Step 4: Place the order
        conf_num = preview.conf_num
        if not conf_num:
            print_error("Preview did not return a confirmation number.")
            raise SystemExit(1)

        result = client.single_option_orders.place_order(order, conf_num)
        if result.is_accepted:
            print_success(f"Order placed! Confirmation: {result.conf_num}")
        else:
            resp_code = None
            if result.order_confirm_detail:
                resp_code = result.order_confirm_detail.resp_type_code
            print_error(f"Order not accepted (respTypeCode={resp_code})")
            raise SystemExit(1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@options_app.command("chain")
@handle_errors
def chain(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Underlying ticker symbol"),
) -> None:
    """Show option chain for an underlying symbol."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    with get_client() as client:
        resp = client.option_chain.get_option_chain(symbol.upper())

        if fmt == "json":
            # Build a serializable dict from the dataclass
            data = {
                "symbol": resp.symbol,
                "calls": [
                    {
                        "date": exp.date,
                        "options": [
                            {
                                "symbol": o.symbol,
                                "contract_symbol": o.contract_symbol,
                                "strike": o.strike,
                                "expiry_type": o.expiry_type,
                            }
                            for o in exp.options
                        ],
                    }
                    for exp in resp.calls
                ],
                "puts": [
                    {
                        "date": exp.date,
                        "options": [
                            {
                                "symbol": o.symbol,
                                "contract_symbol": o.contract_symbol,
                                "strike": o.strike,
                                "expiry_type": o.expiry_type,
                            }
                            for o in exp.options
                        ],
                    }
                    for exp in resp.puts
                ],
            }
            print_json(data)
            return

        # Print calls
        call_rows = []
        for exp in resp.calls:
            for opt in exp.options:
                call_rows.append({
                    "expiry": exp.date,
                    "symbol": opt.symbol,
                    "strike": opt.strike,
                    "type": opt.expiry_type,
                })
        if call_rows:
            print_table(
                rows=call_rows,
                columns=[
                    {"header": "Expiry", "key": "expiry"},
                    {"header": "Symbol", "key": "symbol"},
                    {"header": "Strike", "key": "strike", "justify": "right", "format": "currency"},
                    {"header": "Type", "key": "type"},
                ],
                title=f"Calls - {resp.symbol}",
            )

        # Print puts
        put_rows = []
        for exp in resp.puts:
            for opt in exp.options:
                put_rows.append({
                    "expiry": exp.date,
                    "symbol": opt.symbol,
                    "strike": opt.strike,
                    "type": opt.expiry_type,
                })
        if put_rows:
            print_table(
                rows=put_rows,
                columns=[
                    {"header": "Expiry", "key": "expiry"},
                    {"header": "Symbol", "key": "symbol"},
                    {"header": "Strike", "key": "strike", "justify": "right", "format": "currency"},
                    {"header": "Type", "key": "type"},
                ],
                title=f"Puts - {resp.symbol}",
            )

        if not call_rows and not put_rows:
            print_success(f"No options found for {symbol.upper()}.")


@options_app.command("buy")
@handle_errors
def options_buy(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Option contract symbol (e.g., AAPL250418C00170000)"),
    qty: int = typer.Argument(..., help="Number of contracts"),
    limit: Optional[float] = typer.Option(None, "--limit", help="Limit price (market order if omitted)"),
    tif: str = typer.Option("day", "--tif", help="Time in force: day or gtc"),
    account: Optional[str] = typer.Option(None, "--account", help="Account number"),
    live: bool = typer.Option(False, "--live", help="Actually place the order (default: preview only)"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt (only with --live)"),
) -> None:
    """Preview or place a single-leg option buy order."""
    _option_order(ctx, "buy", symbol, qty, limit, tif, account, live, yes)


@options_app.command("sell")
@handle_errors
def options_sell(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Option contract symbol (e.g., AAPL250418C00170000)"),
    qty: int = typer.Argument(..., help="Number of contracts"),
    limit: Optional[float] = typer.Option(None, "--limit", help="Limit price (market order if omitted)"),
    tif: str = typer.Option("day", "--tif", help="Time in force: day or gtc"),
    account: Optional[str] = typer.Option(None, "--account", help="Account number"),
    live: bool = typer.Option(False, "--live", help="Actually place the order (default: preview only)"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt (only with --live)"),
) -> None:
    """Preview or place a single-leg option sell order."""
    _option_order(ctx, "sell", symbol, qty, limit, tif, account, live, yes)
