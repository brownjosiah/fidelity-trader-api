"""Portfolio commands: accounts, positions, balances."""

from __future__ import annotations

from typing import Optional

import typer

from fidelity_trader.cli._errors import handle_errors
from fidelity_trader.cli._output import print_json, print_table
from fidelity_trader.cli._session import get_client, resolve_account

portfolio_app = typer.Typer(help="Portfolio commands")


@portfolio_app.command("accounts")
@handle_errors
def accounts(
    ctx: typer.Context,
) -> None:
    """List all accounts."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    with get_client() as client:
        resp = client.accounts.discover_accounts()

        if fmt == "json":
            print_json([acct.model_dump(by_alias=True) for acct in resp.accounts])
            return

        rows = []
        for acct in resp.accounts:
            name = ""
            if acct.preference_detail and acct.preference_detail.name:
                name = acct.preference_detail.name
            option_level = None
            if acct.acct_trade_attr_detail:
                option_level = acct.acct_trade_attr_detail.option_level
            rows.append({
                "account": acct.acct_num or "--",
                "type": acct.acct_sub_type_desc or acct.acct_type or "--",
                "name": name or "--",
                "margin": "Yes" if (acct.acct_trade_attr_detail and acct.acct_trade_attr_detail.mrgn_estb) else "No",
                "options": str(option_level) if option_level is not None else "--",
            })

        print_table(
            rows=rows,
            columns=[
                {"header": "Account", "key": "account"},
                {"header": "Type", "key": "type"},
                {"header": "Name", "key": "name"},
                {"header": "Margin", "key": "margin"},
                {"header": "Options Level", "key": "options", "justify": "right"},
            ],
            title="Accounts",
        )


@portfolio_app.command("positions")
@handle_errors
def positions(
    ctx: typer.Context,
    account: Optional[str] = typer.Argument(None, help="Account number (optional)"),
) -> None:
    """Show positions for an account."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"
    account_flag = ctx.obj.get("account") if ctx.obj else None

    with get_client() as client:
        acct_num = account or resolve_account(client, account_flag)
        resp = client.positions.get_positions([acct_num])

        if fmt == "json":
            print_json(resp.model_dump(by_alias=True))
            return

        for acct in resp.accounts:
            rows = []
            for pos in acct.positions:
                last_price = None
                day_change = None
                day_change_pct = None
                if pos.price_detail:
                    last_price = pos.price_detail.last_price
                    day_change = pos.price_detail.last_price_chg
                    day_change_pct = pos.price_detail.last_price_chg_pct

                market_val = None
                total_gl = None
                total_gl_pct = None
                if pos.market_val_detail:
                    market_val = pos.market_val_detail.market_val
                    total_gl = pos.market_val_detail.total_gain_loss
                    total_gl_pct = pos.market_val_detail.total_gain_loss_pct

                avg_cost = None
                if pos.cost_basis_detail:
                    avg_cost = pos.cost_basis_detail.avg_cost_per_share

                rows.append({
                    "symbol": pos.symbol or "--",
                    "description": (pos.security_description or "--")[:30],
                    "quantity": pos.quantity,
                    "last_price": last_price,
                    "day_change": day_change,
                    "day_change_pct": day_change_pct,
                    "market_value": market_val,
                    "avg_cost": avg_cost,
                    "total_gl": total_gl,
                    "total_gl_pct": total_gl_pct,
                })

            print_table(
                rows=rows,
                columns=[
                    {"header": "Symbol", "key": "symbol"},
                    {"header": "Description", "key": "description"},
                    {"header": "Qty", "key": "quantity", "justify": "right", "format": "number"},
                    {"header": "Last", "key": "last_price", "justify": "right", "format": "currency"},
                    {"header": "Day Chg", "key": "day_change", "justify": "right", "format": "currency"},
                    {"header": "Day %", "key": "day_change_pct", "justify": "right", "format": "pct"},
                    {"header": "Mkt Value", "key": "market_value", "justify": "right", "format": "currency"},
                    {"header": "Avg Cost", "key": "avg_cost", "justify": "right", "format": "currency"},
                    {"header": "Total G/L", "key": "total_gl", "justify": "right", "format": "currency"},
                    {"header": "Total %", "key": "total_gl_pct", "justify": "right", "format": "pct"},
                ],
                title=f"Positions - {acct.acct_num}",
            )


@portfolio_app.command("balances")
@handle_errors
def balances(
    ctx: typer.Context,
    account: Optional[str] = typer.Argument(None, help="Account number (optional)"),
) -> None:
    """Show balances for an account."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"
    account_flag = ctx.obj.get("account") if ctx.obj else None

    with get_client() as client:
        acct_num = account or resolve_account(client, account_flag)
        resp = client.balances.get_balances([acct_num])

        if fmt == "json":
            print_json(resp.model_dump(by_alias=True))
            return

        for acct in resp.accounts:
            bal = acct.recent_balance_detail or acct.intraday_balance_detail or acct.close_balance_detail
            if bal is None:
                print(f"No balance data for {acct.acct_num}")
                continue

            rows = []

            # Account value
            if bal.acct_val_detail:
                av = bal.acct_val_detail
                rows.append({"label": "Net Worth", "value": av.net_worth, "change": av.net_worth_chg})
                rows.append({"label": "Market Value", "value": av.market_val, "change": av.market_val_chg})

            # Cash
            if bal.cash_detail:
                cd = bal.cash_detail
                rows.append({"label": "Cash (Held)", "value": cd.held_in_cash, "change": None})
                rows.append({"label": "Core Balance", "value": cd.core_balance, "change": None})

            # Buying power
            if bal.buying_power_detail:
                bp = bal.buying_power_detail
                rows.append({"label": "Buying Power (Cash)", "value": bp.cash, "change": bp.cash_chg})
                rows.append({"label": "Buying Power (Margin)", "value": bp.margin, "change": bp.margin_chg})
                if bp.day_trade is not None:
                    rows.append({"label": "Day Trade BP", "value": bp.day_trade, "change": None})

            # Available to withdraw
            if bal.available_to_withdraw_detail:
                aw = bal.available_to_withdraw_detail
                rows.append({"label": "Available to Withdraw (Cash)", "value": aw.cash_only, "change": None})

            print_table(
                rows=rows,
                columns=[
                    {"header": "Metric", "key": "label"},
                    {"header": "Value", "key": "value", "justify": "right", "format": "currency"},
                    {"header": "Change", "key": "change", "justify": "right", "format": "currency"},
                ],
                title=f"Balances - {acct.acct_num}",
            )
