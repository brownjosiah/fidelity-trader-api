"""Market data commands: quote, chart, search."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

import typer

from fidelity_trader.cli._errors import handle_errors
from fidelity_trader.cli._output import print_json, print_table
from fidelity_trader.cli._session import get_client

market_data_app = typer.Typer(help="Market data commands")

# Bar width choices for chart command
_BAR_CHOICES = ["1", "5", "15", "30", "60", "D", "W", "M"]


@market_data_app.command("quote")
@handle_errors
def quote(
    ctx: typer.Context,
    symbols: List[str] = typer.Argument(..., help="One or more ticker symbols"),
) -> None:
    """Get fast quotes for one or more symbols."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    with get_client() as client:
        rows = []
        for sym in symbols:
            # Use the chart endpoint to get current quote data.
            # A 1-day daily bar fetch gives us the ChartSymbolInfo with
            # last trade, change, etc.
            now = datetime.now()
            start = (now - timedelta(days=1)).strftime("%Y/%m/%d-00:00:00")
            end = now.strftime("%Y/%m/%d-23:59:59")
            resp = client.chart.get_chart(
                symbol=sym.upper(),
                start_date=start,
                end_date=end,
                bar_width="D",
                extended_hours=False,
            )
            info = resp.symbol_info
            rows.append({
                "symbol": info.identifier,
                "last": info.last_trade,
                "change": info.net_change,
                "change_pct": info.net_change_pct,
                "open": info.day_open,
                "high": info.day_high,
                "low": info.day_low,
                "prev_close": info.previous_close,
            })

        if fmt == "json":
            print_json(rows)
            return

        print_table(
            rows=rows,
            columns=[
                {"header": "Symbol", "key": "symbol"},
                {"header": "Last", "key": "last", "justify": "right", "format": "currency"},
                {"header": "Change", "key": "change", "justify": "right", "format": "number"},
                {"header": "Change%", "key": "change_pct", "justify": "right", "format": "pct"},
                {"header": "Open", "key": "open", "justify": "right", "format": "currency"},
                {"header": "High", "key": "high", "justify": "right", "format": "currency"},
                {"header": "Low", "key": "low", "justify": "right", "format": "currency"},
                {"header": "Prev Close", "key": "prev_close", "justify": "right", "format": "currency"},
            ],
            title="Quotes",
        )


@market_data_app.command("chart")
@handle_errors
def chart(
    ctx: typer.Context,
    symbol: str = typer.Argument(..., help="Ticker symbol"),
    bars: str = typer.Option("D", "--bars", "-b", help="Bar width: 1, 5, 15, 30, 60, D, W, M"),
    days: int = typer.Option(5, "--days", "-d", help="Lookback days"),
) -> None:
    """Get historical chart data (OHLCV bars)."""
    if bars not in _BAR_CHOICES:
        from fidelity_trader.cli._output import print_error
        print_error(f"Invalid bar width '{bars}'. Choose from: {', '.join(_BAR_CHOICES)}")
        raise SystemExit(1)

    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    now = datetime.now()
    start = (now - timedelta(days=days)).strftime("%Y/%m/%d-00:00:00")
    end = now.strftime("%Y/%m/%d-23:59:59")

    with get_client() as client:
        resp = client.chart.get_chart(
            symbol=symbol.upper(),
            start_date=start,
            end_date=end,
            bar_width=bars,
            extended_hours=(bars not in ("D", "W", "M")),
        )

        if fmt == "json":
            bar_dicts = [
                {
                    "timestamp": b.timestamp,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                }
                for b in resp.bars
            ]
            print_json(bar_dicts)
            return

        rows = [
            {
                "timestamp": b.timestamp,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in resp.bars
        ]

        print_table(
            rows=rows,
            columns=[
                {"header": "Time", "key": "timestamp"},
                {"header": "Open", "key": "open", "justify": "right", "format": "currency"},
                {"header": "High", "key": "high", "justify": "right", "format": "currency"},
                {"header": "Low", "key": "low", "justify": "right", "format": "currency"},
                {"header": "Close", "key": "close", "justify": "right", "format": "currency"},
                {"header": "Volume", "key": "volume", "justify": "right"},
            ],
            title=f"Chart - {resp.symbol_info.identifier} ({bars} bars, {days}d)",
        )


@market_data_app.command("search")
@handle_errors
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query (symbol or name)"),
) -> None:
    """Search for symbols by name or ticker."""
    fmt = ctx.obj.get("format", "table") if ctx.obj else "table"

    with get_client() as client:
        resp = client.search.autosuggest(query)

        if fmt == "json":
            print_json([s.model_dump(by_alias=True) for s in resp.suggestions])
            return

        if not resp.suggestions:
            from fidelity_trader.cli._output import print_error
            print_error(f"No results for '{query}'")
            raise SystemExit(1)

        rows = [
            {
                "symbol": s.symbol,
                "description": s.desc or "--",
                "type": s.type or "--",
                "exchange": s.exchange or "--",
            }
            for s in resp.suggestions
        ]

        print_table(
            rows=rows,
            columns=[
                {"header": "Symbol", "key": "symbol"},
                {"header": "Description", "key": "description"},
                {"header": "Type", "key": "type"},
                {"header": "Exchange", "key": "exchange"},
            ],
            title=f"Search Results ({resp.count})",
        )
