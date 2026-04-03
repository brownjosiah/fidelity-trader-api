"""Output formatting helpers for the ft CLI."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich.console import Console
from rich.json import JSON as RichJSON
from rich.table import Table

_console = Console()
_err_console = Console(stderr=True)


def _format_currency(value: float | None) -> str:
    """Format a float as currency with color markup for rich."""
    if value is None:
        return "--"
    prefix = "-" if value < 0 else ""
    formatted = f"{prefix}${abs(value):,.2f}"
    if value < 0:
        return f"[red]{formatted}[/red]"
    elif value > 0:
        return f"[green]{formatted}[/green]"
    return formatted


def _format_number(value: float | None, decimals: int = 2) -> str:
    """Format a float with color markup for rich."""
    if value is None:
        return "--"
    formatted = f"{value:,.{decimals}f}"
    if value < 0:
        return f"[red]{formatted}[/red]"
    elif value > 0:
        return f"[green]{formatted}[/green]"
    return formatted


def _format_pct(value: float | None) -> str:
    """Format a float as a percentage with color markup for rich."""
    if value is None:
        return "--"
    formatted = f"{value:,.2f}%"
    if value < 0:
        return f"[red]{formatted}[/red]"
    elif value > 0:
        return f"[green]{formatted}[/green]"
    return formatted


def print_table(
    rows: list[dict[str, Any]],
    columns: list[dict[str, str]],
    title: str | None = None,
) -> None:
    """Print a rich table from rows and column definitions.

    Each column dict should have:
      - header: Display name
      - key: Key to look up in each row dict
      - justify: "left", "right", or "center" (default "left")
      - format: Optional — "currency", "number", "pct" for special formatting
    """
    table = Table(title=title, show_lines=False, expand=False)

    for col in columns:
        table.add_column(
            col["header"],
            justify=col.get("justify", "left"),
            no_wrap=col.get("no_wrap", False),
        )

    for row in rows:
        cells: list[str] = []
        for col in columns:
            value = row.get(col["key"])
            fmt = col.get("format")
            if fmt == "currency":
                cells.append(_format_currency(value))
            elif fmt == "number":
                cells.append(_format_number(value))
            elif fmt == "pct":
                cells.append(_format_pct(value))
            else:
                cells.append(str(value) if value is not None else "--")
        table.add_row(*cells)

    _console.print(table)


def print_json(data: Any) -> None:
    """Print JSON — highlighted in terminal, plain when piped."""
    if sys.stdout.isatty():
        _console.print(RichJSON(json.dumps(data, default=str)))
    else:
        print(json.dumps(data, indent=2, default=str))


def print_error(message: str) -> None:
    """Print an error message in red to stderr."""
    _err_console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print a success message in green."""
    _console.print(f"[bold green]{message}[/bold green]")
