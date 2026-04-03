"""Order commands: orders, buy, sell, cancel."""

from __future__ import annotations

from typing import Optional

import typer

from fidelity_trader.cli._errors import handle_errors
from fidelity_trader.cli._output import print_error, print_json, print_success, print_table
from fidelity_trader.cli._session import get_client, resolve_account
from fidelity_trader.models.equity_order import EquityOrderRequest

orders_app = typer.Typer(help="Order commands")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_price_type(
    limit: float | None,
    stop: float | None,
) -> tuple[str, float | None, float | None]:
    """Return (priceTypeCode, limitPrice, stopPrice) from CLI flags."""
    if limit is not None and stop is not None:
        return "SL", limit, stop
    if stop is not None:
        return "S", None, stop
    if limit is not None:
        return "L", limit, None
    return "M", None, None


_TIF_MAP = {"day": "D", "gtc": "G"}
_ACTION_MAP = {"buy": "B", "sell": "S"}
_PRICE_DESC = {"M": "Market", "L": "Limit", "S": "Stop", "SL": "Stop Limit"}


def _display_equity_preview(preview, order: EquityOrderRequest) -> None:
    """Print a formatted preview summary for an equity order."""
    confirm = preview.order_confirm_detail
    action_desc = "Buy" if order.order_action_code == "B" else "Sell"
    price_desc = _PRICE_DESC.get(order.price_type_code, order.price_type_code)

    price_str = "Market"
    if order.price_type_code == "L" and order.limit_price is not None:
        price_str = f"${order.limit_price:,.2f}"
    elif order.price_type_code == "S" and confirm and confirm.order_detail:
        price_str = "Stop"
    elif order.price_type_code == "SL" and order.limit_price is not None:
        price_str = f"${order.limit_price:,.2f} (stop limit)"

    est_cost = None
    commission = None
    if confirm:
        est_cost = confirm.net_amount
        if confirm.est_commission_detail:
            commission = confirm.est_commission_detail.est_commission

    rows = [
        {"field": "Action", "value": action_desc},
        {"field": "Symbol", "value": order.symbol},
        {"field": "Quantity", "value": str(int(order.qty))},
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
        title="Order Preview",
    )


def _equity_order(
    ctx: typer.Context,
    action: str,
    symbol: str,
    qty: int,
    limit: float | None,
    stop: float | None,
    tif: str,
    account: str | None,
    live: bool,
    yes: bool,
) -> None:
    """Shared logic for buy/sell commands."""
    account_flag = ctx.obj.get("account") if ctx.obj else None
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    price_type_code, limit_price, stop_price = _resolve_price_type(limit, stop)
    tif_code = _TIF_MAP.get(tif, "D")
    action_code = _ACTION_MAP[action]

    # Always create client with live_trading=True for CLI -- the CLI manages
    # its own dry-run UX (preview + confirmation prompt).
    with get_client(live_trading=True) as client:
        acct_num = account or resolve_account(client, account_flag)

        order = EquityOrderRequest(
            acct_num=acct_num,
            symbol=symbol.upper(),
            order_action_code=action_code,
            qty=float(qty),
            price_type_code=price_type_code,
            limit_price=limit_price,
            tif_code=tif_code,
        )

        # Step 1: Always preview first
        preview = client.equity_orders.preview_order(order)

        if fmt == "json":
            preview_data = preview.model_dump(by_alias=True)
            preview_data["_dry_run"] = not live
            print_json(preview_data)
            if not live:
                return
        else:
            _display_equity_preview(preview, order)

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

        result = client.equity_orders.place_order(order, conf_num)
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


@orders_app.command("orders")
@handle_errors
def orders(
    ctx: typer.Context,
    account: Optional[str] = typer.Argument(None, help="Account number (optional)"),
) -> None:
    """List open/recent orders."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"
    account_flag = ctx.obj.get("account") if ctx.obj else None

    with get_client() as client:
        acct_num = account or resolve_account(client, account_flag)
        resp = client.order_status.get_order_status([acct_num])

        if fmt == "json":
            print_json(resp.model_dump(by_alias=True))
            return

        if not resp.orders:
            print_success("No open or recent orders.")
            return

        rows = []
        for o in resp.orders:
            conf_num = "--"
            if o.id_detail and o.id_detail.conf_num:
                conf_num = o.id_detail.conf_num

            symbol = "--"
            action = "--"
            qty = "--"
            if o.base_order_detail:
                if o.base_order_detail.security_detail and o.base_order_detail.security_detail.symbol:
                    symbol = o.base_order_detail.security_detail.symbol
                action = o.base_order_detail.action_code_desc or o.base_order_detail.order_action_code or "--"
                qty = str(int(o.base_order_detail.qty)) if o.base_order_detail.qty is not None else "--"

            status = "--"
            cancelable = ""
            if o.status_detail:
                status = o.status_detail.status_desc or o.status_detail.status_code or "--"
                if o.status_detail.cancelable_ind:
                    cancelable = "Yes"

            price_type = "--"
            if o.tradable_sec_order_detail and o.tradable_sec_order_detail.price_type_detail:
                ptd = o.tradable_sec_order_detail.price_type_detail
                price_type = ptd.price_type_desc or ptd.price_type_code or "--"

            rows.append({
                "conf_num": conf_num,
                "symbol": symbol,
                "action": action,
                "qty": qty,
                "type": price_type,
                "status": status,
                "cancelable": cancelable,
            })

        print_table(
            rows=rows,
            columns=[
                {"header": "Conf #", "key": "conf_num"},
                {"header": "Symbol", "key": "symbol"},
                {"header": "Action", "key": "action"},
                {"header": "Qty", "key": "qty", "justify": "right"},
                {"header": "Type", "key": "type"},
                {"header": "Status", "key": "status"},
                {"header": "Cancel?", "key": "cancelable"},
            ],
            title=f"Orders - {acct_num}",
        )


@orders_app.command("buy")
@handle_errors
def buy(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Ticker symbol"),
    qty: int = typer.Argument(..., help="Number of shares"),
    limit: Optional[float] = typer.Option(None, "--limit", help="Limit price (market order if omitted)"),
    stop: Optional[float] = typer.Option(None, "--stop", help="Stop price"),
    tif: str = typer.Option("day", "--tif", help="Time in force: day or gtc"),
    account: Optional[str] = typer.Option(None, "--account", help="Account number"),
    live: bool = typer.Option(False, "--live", help="Actually place the order (default: preview only)"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt (only with --live)"),
) -> None:
    """Preview or place an equity buy order."""
    _equity_order(ctx, "buy", symbol, qty, limit, stop, tif, account, live, yes)


@orders_app.command("sell")
@handle_errors
def sell(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Ticker symbol"),
    qty: int = typer.Argument(..., help="Number of shares"),
    limit: Optional[float] = typer.Option(None, "--limit", help="Limit price (market order if omitted)"),
    stop: Optional[float] = typer.Option(None, "--stop", help="Stop price"),
    tif: str = typer.Option("day", "--tif", help="Time in force: day or gtc"),
    account: Optional[str] = typer.Option(None, "--account", help="Account number"),
    live: bool = typer.Option(False, "--live", help="Actually place the order (default: preview only)"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt (only with --live)"),
) -> None:
    """Preview or place an equity sell order."""
    _equity_order(ctx, "sell", symbol, qty, limit, stop, tif, account, live, yes)


@orders_app.command("cancel")
@handle_errors
def cancel(
    ctx: typer.Context,
    conf_num: str = typer.Argument(..., help="Confirmation number of the order to cancel"),
    account: Optional[str] = typer.Option(None, "--account", help="Account number"),
) -> None:
    """Cancel an open order."""
    account_flag = ctx.obj.get("account") if ctx.obj else None

    with get_client() as client:
        acct_num = account or resolve_account(client, account_flag)
        result = client.cancel_order.cancel_order(
            conf_num=conf_num,
            acct_num=acct_num,
            action_code="B",  # action_code is required but cancel accepts any
        )

        if result.is_accepted:
            print_success(f"Order {conf_num} cancelled.")
        else:
            print_error(f"Cancel request for {conf_num} was not accepted.")
            raise SystemExit(1)
