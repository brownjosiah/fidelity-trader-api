"""Models for historical chart data responses from the fastquote endpoint.

Responses come as JSONP-wrapped JSON from:
  GET https://fastquote.fidelity.com/service/marketdata/historical/chart/json

Traffic captured from Fidelity Trader+ desktop application.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChartBar:
    """A single OHLCV bar from the BarRecord list."""

    timestamp: str   # lt — datetime string, e.g. "2026/03/30-04:00:00"
    open: float      # op
    close: float     # cl
    high: float      # hi
    low: float       # lo
    volume: int      # v

    @classmethod
    def from_dict(cls, record: dict) -> "ChartBar":
        return cls(
            timestamp=record.get("lt", ""),
            open=float(record.get("op", "0")),
            close=float(record.get("cl", "0")),
            high=float(record.get("hi", "0")),
            low=float(record.get("lo", "0")),
            volume=int(record.get("v", "0")),
        )


@dataclass
class ChartSymbolInfo:
    """Metadata and current-day quote fields from the Symbol array entry."""

    identifier: str
    description: str
    last_trade: float
    trade_date: str
    day_open: float
    day_high: float
    day_low: float
    net_change: float
    net_change_pct: float
    previous_close: float

    @classmethod
    def from_dict(cls, data: dict) -> "ChartSymbolInfo":
        return cls(
            identifier=data.get("Identifier", ""),
            description=data.get("Description", ""),
            last_trade=float(data.get("LastTrade", "0")),
            trade_date=data.get("TradeDate", ""),
            day_open=float(data.get("DayOpen", "0")),
            day_high=float(data.get("DayHigh", "0")),
            day_low=float(data.get("DayLow", "0")),
            net_change=float(data.get("NetChange", "0")),
            net_change_pct=float(data.get("NetChangePercent", "0")),
            previous_close=float(data.get("PreviousClose", "0")),
        )


@dataclass
class ChartResponse:
    """Parsed response from the historical/chart/json endpoint."""

    symbol_info: ChartSymbolInfo
    bars: list[ChartBar] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ChartResponse":
        """Parse from the unwrapped JSON dict.

        Expects the top-level structure:
          {"Symbol": [{ ..., "BarList": {"BarRecord": [...]} }]}
        """
        symbols = data.get("Symbol", [])
        if not symbols:
            raise ValueError("ChartResponse: 'Symbol' list is empty or missing")

        sym = symbols[0]
        symbol_info = ChartSymbolInfo.from_dict(sym)

        bar_list = sym.get("BarList", {})
        records = bar_list.get("BarRecord", [])
        if isinstance(records, dict):
            # API may return a single bar as a plain dict instead of a list
            records = [records]

        bars = [ChartBar.from_dict(r) for r in records]
        return cls(symbol_info=symbol_info, bars=bars)
