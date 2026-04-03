"""Streaming command: live quote display via MDDS WebSocket."""

from __future__ import annotations

import asyncio
from typing import List

import typer

from fidelity_trader.cli._errors import handle_errors
from fidelity_trader.cli._output import print_error

stream_app = typer.Typer(help="Streaming commands")

# Default fields to display in the streaming table
_DEFAULT_FIELDS = "last,bid,ask,volume"


@stream_app.command("stream")
@handle_errors
def stream(
    ctx: typer.Context,
    symbols: List[str] = typer.Argument(..., help="One or more ticker symbols"),
    fields: str = typer.Option(
        _DEFAULT_FIELDS,
        "--fields",
        "-F",
        help="Comma-separated fields to display (e.g., last,bid,ask,volume,change)",
    ),
) -> None:
    """Stream live quotes via MDDS WebSocket.

    Displays a real-time updating table of quote data.
    Press Ctrl+C to stop.
    """
    try:
        import websockets  # noqa: F401
    except ImportError:
        print_error("The 'websockets' package is required for streaming. Install it with: pip install websockets")
        raise SystemExit(1)

    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    asyncio.run(_stream_quotes(symbols, field_list))


async def _stream_quotes(symbols: list[str], display_fields: list[str]) -> None:
    """Connect to MDDS and stream quotes with a live-updating display."""
    import websockets

    from rich.console import Console
    from rich.live import Live
    from rich.table import Table

    from fidelity_trader import FidelityClient
    from fidelity_trader.cli._session import load_session_data
    from fidelity_trader.streaming.mdds import MDDSClient, MDDSQuote, MDDS_URL

    # Load session
    data = load_session_data()
    if data is None:
        print_error("Not logged in. Run `ft login` first.")
        raise SystemExit(1)

    cookies = data.get("cookies", {})
    console = Console()

    # Create client and enable auto-refresh
    client = FidelityClient()
    try:
        # Inject saved cookies
        for name, value in cookies.items():
            client._http.cookies.set(name, value, domain=".fidelity.com")
        client._auth._authenticated = True
        client.enable_auto_refresh(interval=300)

        # Create MDDS client
        mdds = MDDSClient()
        upper_symbols = [s.upper() for s in symbols]

        # Field name mapping for display
        field_display = {
            "last": "Last",
            "bid": "Bid",
            "ask": "Ask",
            "volume": "Volume",
            "change": "Change",
            "change_pct": "Change%",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "prev_close": "Prev Close",
            "name": "Name",
        }

        # Map display field names to MDDSQuote data keys
        field_data_keys = {
            "last": "last_price",
            "bid": "bid",
            "ask": "ask",
            "volume": "total_volume",
            "change": "net_change",
            "change_pct": "net_change_pct",
            "open": "open",
            "high": "day_high",
            "low": "day_low",
            "prev_close": "previous_close",
            "name": "security_name",
        }

        # Track latest data for each symbol
        quote_data: dict[str, dict] = {s: {} for s in upper_symbols}

        # Build cookie header for WebSocket
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        extra_headers = {"Cookie": cookie_str}

        console.print(f"[bold]Connecting to MDDS for: {', '.join(upper_symbols)}[/bold]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        def _build_table() -> Table:
            """Build a rich Table from current quote data."""
            table = Table(title="Live Quotes", expand=False)
            table.add_column("Symbol", style="bold")
            for f in display_fields:
                header = field_display.get(f, f.title())
                table.add_column(header, justify="right")

            for sym in upper_symbols:
                data = quote_data.get(sym, {})
                cells = [sym]
                for f in display_fields:
                    key = field_data_keys.get(f, f)
                    val = data.get(key)
                    if val is None or val == "":
                        cells.append("--")
                    elif f in ("volume",):
                        try:
                            cells.append(f"{int(val):,}")
                        except (ValueError, TypeError):
                            cells.append(str(val))
                    elif f in ("change_pct",):
                        try:
                            fval = float(val)
                            color = "green" if fval >= 0 else "red"
                            cells.append(f"[{color}]{fval:,.2f}%[/{color}]")
                        except (ValueError, TypeError):
                            cells.append(str(val))
                    elif f in ("change",):
                        try:
                            fval = float(val)
                            color = "green" if fval >= 0 else "red"
                            cells.append(f"[{color}]{fval:,.2f}[/{color}]")
                        except (ValueError, TypeError):
                            cells.append(str(val))
                    elif f in ("last", "bid", "ask", "open", "high", "low", "prev_close"):
                        try:
                            cells.append(f"${float(val):,.2f}")
                        except (ValueError, TypeError):
                            cells.append(str(val))
                    else:
                        cells.append(str(val))
                table.add_row(*cells)

            return table

        try:
            async with websockets.connect(
                MDDS_URL,
                additional_headers=extra_headers,
            ) as ws:
                # Read connection message
                connect_msg = await ws.recv()
                session = mdds.handle_connect_message(connect_msg)

                if not session.connected:
                    print_error("MDDS connection failed.")
                    raise SystemExit(1)

                # Subscribe
                sub_msg = mdds.build_subscribe_message(upper_symbols)
                await ws.send(sub_msg)

                # Stream with live display
                with Live(_build_table(), console=console, refresh_per_second=4) as live:
                    async for raw in ws:
                        updates = mdds.parse_message(raw)
                        for update in updates:
                            if isinstance(update, MDDSQuote) and update.symbol in quote_data:
                                # Merge new data into existing
                                quote_data[update.symbol].update(
                                    {k: v for k, v in update.data.items() if v is not None and v != ""}
                                )
                        live.update(_build_table())

        except KeyboardInterrupt:
            pass
        except Exception as exc:
            print_error(f"Streaming error: {exc}")
            raise SystemExit(1)

    finally:
        client.disable_auto_refresh()
        client.close()
        console.print("\n[bold]Stream stopped.[/bold]")
