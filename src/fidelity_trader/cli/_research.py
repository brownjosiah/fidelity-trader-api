"""Research commands: earnings, dividends."""

from __future__ import annotations

from typing import List

import typer

from fidelity_trader.cli._errors import handle_errors
from fidelity_trader.cli._output import print_json, print_table
from fidelity_trader.cli._session import get_client

research_app = typer.Typer(help="Research commands")


@research_app.command("earnings")
@handle_errors
def earnings(
    ctx: typer.Context,
    symbols: List[str] = typer.Argument(..., help="One or more ticker symbols"),
) -> None:
    """Get earnings data for symbols."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    with get_client() as client:
        resp = client.research.get_earnings([s.upper() for s in symbols])

        if fmt == "json":
            print_json([e.model_dump(by_alias=True) for e in resp.earnings])
            return

        for detail in resp.earnings:
            symbol = "--"
            if detail.sec_detail and detail.sec_detail.symbol:
                symbol = detail.sec_detail.symbol

            rows = []
            for q in detail.quarters:
                rows.append({
                    "quarter": f"Q{q.fiscal_qtr} {q.fiscal_yr}",
                    "report_date": q.report_date or "--",
                    "adjusted_eps": q.adjusted_eps,
                    "consensus_est": q.consensus_est,
                    "surprise": (
                        q.adjusted_eps - q.consensus_est
                        if q.adjusted_eps is not None and q.consensus_est is not None
                        else None
                    ),
                })

            print_table(
                rows=rows,
                columns=[
                    {"header": "Quarter", "key": "quarter"},
                    {"header": "Report Date", "key": "report_date"},
                    {"header": "EPS", "key": "adjusted_eps", "justify": "right", "format": "number"},
                    {"header": "Estimate", "key": "consensus_est", "justify": "right", "format": "number"},
                    {"header": "Surprise", "key": "surprise", "justify": "right", "format": "number"},
                ],
                title=f"Earnings - {symbol}",
            )


@research_app.command("dividends")
@handle_errors
def dividends(
    ctx: typer.Context,
    symbols: List[str] = typer.Argument(..., help="One or more ticker symbols"),
) -> None:
    """Get dividend data for symbols."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    with get_client() as client:
        resp = client.research.get_dividends([s.upper() for s in symbols])

        if fmt == "json":
            print_json([d.model_dump(by_alias=True) for d in resp.dividends])
            return

        for detail in resp.dividends:
            symbol = "--"
            if detail.sec_detail and detail.sec_detail.symbol:
                symbol = detail.sec_detail.symbol

            # Summary row
            summary_rows = [
                {"label": "Last Dividend", "value": detail.amt},
                {"label": "Ex-Dividend Date", "value": detail.ex_div_date},
                {"label": "Yield (TTM)", "value": detail.yld_ttm},
                {"label": "Indicated Annual Div", "value": detail.indicated_ann_div},
            ]
            formatted_summary = []
            for row in summary_rows:
                val = row["value"]
                if val is None:
                    display = "--"
                elif isinstance(val, float):
                    display = f"{val:.4f}" if row["label"] == "Yield (TTM)" else f"${val:.2f}"
                else:
                    display = str(val)
                formatted_summary.append({"label": row["label"], "display": display})

            print_table(
                rows=formatted_summary,
                columns=[
                    {"header": "Metric", "key": "label"},
                    {"header": "Value", "key": "display", "justify": "right"},
                ],
                title=f"Dividends - {symbol}",
            )

            # History table if available
            if detail.history:
                hist_rows = [
                    {
                        "ex_date": h.ex_date or "--",
                        "pay_date": h.pay_date or "--",
                        "amount": h.amt,
                        "frequency": h.freq_name or "--",
                        "type": h.type or "--",
                    }
                    for h in detail.history[:10]  # Show recent 10
                ]

                print_table(
                    rows=hist_rows,
                    columns=[
                        {"header": "Ex-Date", "key": "ex_date"},
                        {"header": "Pay Date", "key": "pay_date"},
                        {"header": "Amount", "key": "amount", "justify": "right", "format": "currency"},
                        {"header": "Frequency", "key": "frequency"},
                        {"header": "Type", "key": "type"},
                    ],
                    title=f"Dividend History - {symbol}",
                )
