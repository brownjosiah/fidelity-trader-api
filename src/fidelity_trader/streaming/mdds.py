"""MDDS WebSocket client for real-time market data streaming.

Connects to Fidelity's Market Data Distribution System via WebSocket.
Uses the session cookies from login for authentication.
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Optional, Union

from fidelity_trader.streaming.mdds_fields import (
    parse_fields,
)


MDDS_URL = "wss://mdds-i-tc.fidelity.com/?productid=atn"


@dataclass
class MDDSQuote:
    """A parsed quote update from the MDDS stream."""
    symbol: str
    security_type: str = ""
    data: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    @property
    def last_price(self) -> Optional[float]:
        v = self.data.get("last_price")
        return float(v) if v else None

    @property
    def bid(self) -> Optional[float]:
        v = self.data.get("bid")
        return float(v) if v else None

    @property
    def ask(self) -> Optional[float]:
        v = self.data.get("ask")
        return float(v) if v else None

    @property
    def volume(self) -> Optional[int]:
        v = self.data.get("volume") or self.data.get("total_volume")
        return int(v) if v else None

    @property
    def net_change(self) -> Optional[float]:
        v = self.data.get("net_change")
        return float(v) if v else None

    @property
    def delta(self) -> Optional[float]:
        v = self.data.get("delta")
        return float(v) if v else None

    @property
    def last_trade_price(self) -> Optional[float]:
        v = self.data.get("last_trade_price")
        return float(v) if v else None

    @property
    def last_trade_size(self) -> Optional[int]:
        v = self.data.get("last_trade_size")
        return int(v) if v else None

    @property
    def last_trade_time(self) -> Optional[str]:
        return self.data.get("last_trade_time") or None

    @property
    def last_trade_exchange(self) -> Optional[str]:
        return self.data.get("last_trade_exchange") or None

    @property
    def is_option(self) -> bool:
        return self.security_type == "OP"

    @property
    def has_trade_data(self) -> bool:
        return self.last_trade_price is not None


def _to_float(v: Optional[str]) -> Optional[float]:
    """Convert a string to float, returning None for missing/empty values."""
    if v is None or v == "":
        return None
    return float(v)


def _to_int(v: Optional[str]) -> Optional[int]:
    """Convert a string to int, returning None for missing/empty values."""
    if v is None or v == "":
        return None
    return int(v)


@dataclass
class BookLevel:
    """A single price level in the L2 order book."""
    price: Optional[float] = None
    size: Optional[int] = None
    exchange: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class VirtualBook:
    """A parsed L2 depth-of-book update from the MDDS stream.

    Contains 25 bid levels and 25 ask levels.  Index 0 is the best
    bid/ask (top of book).
    """
    symbol: str
    bids: list[BookLevel] = field(default_factory=list)
    asks: list[BookLevel] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def best_bid(self) -> Optional[BookLevel]:
        if self.bids and self.bids[0].price is not None:
            return self.bids[0]
        return None

    @property
    def best_ask(self) -> Optional[BookLevel]:
        if self.asks and self.asks[0].price is not None:
            return self.asks[0]
        return None

    @property
    def spread(self) -> Optional[float]:
        bb = self.best_bid
        ba = self.best_ask
        if bb is not None and ba is not None:
            return round(ba.price - bb.price, 4)
        return None

    @property
    def mid_price(self) -> Optional[float]:
        bb = self.best_bid
        ba = self.best_ask
        if bb is not None and ba is not None:
            return round((bb.price + ba.price) / 2, 4)
        return None

    @classmethod
    def from_fields(cls, symbol: str, data: dict, raw: dict) -> "VirtualBook":
        """Build a VirtualBook from parsed field data."""
        bids = []
        for i in range(25):
            bids.append(BookLevel(
                price=_to_float(data.get(f"bid_price_{i}")),
                size=_to_int(data.get(f"bid_size_{i}")),
                exchange=data.get(f"bid_exchange_{i}"),
                timestamp=data.get(f"bid_time_{i}"),
            ))
        asks = []
        for i in range(25):
            asks.append(BookLevel(
                price=_to_float(data.get(f"ask_price_{i}")),
                size=_to_int(data.get(f"ask_size_{i}")),
                exchange=data.get(f"ask_exchange_{i}"),
                timestamp=data.get(f"ask_time_{i}"),
            ))
        return cls(symbol=symbol, bids=bids, asks=asks, raw=raw)


@dataclass
class MDDSSession:
    """Connection state for an MDDS WebSocket session."""
    session_id: str = ""
    host: str = ""
    connected: bool = False


class MDDSClient:
    """Client for Fidelity's MDDS real-time market data WebSocket.

    Usage:
        client = MDDSClient()
        client.connect(cookies)
        client.subscribe([".SPX", "AAPL"], on_quote=my_callback)
        # ... quotes stream in via callback ...
        client.close()

    Note: Requires the `websockets` library for actual WebSocket connections.
    This module provides the protocol layer (message building/parsing).
    For testing and development, use build_subscribe_message() and
    parse_message() directly.
    """

    def __init__(self) -> None:
        self._session = MDDSSession()
        self._callbacks: list[Callable[[MDDSQuote], None]] = []

    @property
    def session_id(self) -> str:
        return self._session.session_id

    @property
    def is_connected(self) -> bool:
        return self._session.connected

    def handle_connect_message(self, raw: str) -> MDDSSession:
        """Parse the initial connection message from the server."""
        data = json.loads(raw)
        self._session = MDDSSession(
            session_id=data.get("SessionId", ""),
            host=data.get("host", ""),
            connected=data.get("Status") == "Ok",
        )
        return self._session

    def build_subscribe_message(
        self,
        symbols: list[str],
        conflation_rate: int = 1000,
        include_greeks: bool = True,
    ) -> str:
        """Build a subscribe command message."""
        return json.dumps({
            "SessionId": self._session.session_id,
            "Command": "subscribe",
            "Symbol": ",".join(symbols),
            "ConflationRate": conflation_rate,
            "IncludeGreeks": include_greeks,
        })

    def build_unsubscribe_message(self, symbols: list[str]) -> str:
        """Build an unsubscribe command message."""
        return json.dumps({
            "SessionId": self._session.session_id,
            "Command": "unsubscribe",
            "Symbol": ",".join(symbols),
        })

    def build_virtualbook_subscribe(
        self,
        symbol: str,
        conflation_rate: int = 1000,
        include_arca_only: bool = True,
    ) -> str:
        """Build a subscribe_virtualbook message for L2 depth."""
        return json.dumps({
            "SessionId": self._session.session_id,
            "Command": "subscribe_virtualbook",
            "Symbol": symbol,
            "ConflationRate": conflation_rate,
            "IncludeArcaOnly": include_arca_only,
        })

    def build_virtualbook_unsubscribe(self, symbol: str) -> str:
        """Build an unsubscribe_virtualbook message."""
        return json.dumps({
            "SessionId": self._session.session_id,
            "Command": "unsubscribe_virtualbook",
            "Symbol": symbol,
        })

    @staticmethod
    def _strip_vb_suffix(symbol: str) -> str:
        """Strip the .VB suffix from virtualbook symbols."""
        if symbol.endswith(".VB"):
            return symbol[:-3]
        return symbol

    def parse_message(self, raw: str) -> list[Union[MDDSQuote, VirtualBook]]:
        """Parse a server message into quote or virtualbook updates.

        Returns a list of ``MDDSQuote`` for regular subscribe messages or
        ``VirtualBook`` for subscribe_virtualbook messages.
        Returns empty list for error messages or non-data messages.
        """
        data = json.loads(raw)

        # Connection message
        if "SessionId" in data and "Message" in data:
            self.handle_connect_message(raw)
            return []

        # Error response
        if data.get("ResponseType") == "-1":
            return []

        is_virtualbook = data.get("Command") == "subscribe_virtualbook"

        # Success response with data (initial snapshot)
        if data.get("ResponseType") == "1" and "Data" in data:
            results: list[Union[MDDSQuote, VirtualBook]] = []
            for item in data["Data"]:
                if item.get("0") != "success":
                    continue
                symbol = item.get("6", item.get("289", ""))
                if is_virtualbook:
                    symbol = self._strip_vb_suffix(symbol)
                    parsed = parse_fields(item)
                    results.append(VirtualBook.from_fields(symbol, parsed, item))
                else:
                    sec_type = item.get("128", "")
                    parsed = parse_fields(item)
                    results.append(MDDSQuote(
                        symbol=symbol,
                        security_type=sec_type,
                        data=parsed,
                        raw=item,
                    ))
            return results

        # Streaming tick updates (T&S data, live price changes, VB deltas)
        if data.get("ResponseType") == "0" and "Data" in data:
            results = []
            for item in data["Data"]:
                symbol = item.get("6", item.get("289", ""))
                if is_virtualbook:
                    symbol = self._strip_vb_suffix(symbol)
                    parsed = parse_fields(item)
                    results.append(VirtualBook.from_fields(symbol, parsed, item))
                else:
                    sec_type = item.get("128", "")
                    parsed = parse_fields(item)
                    results.append(MDDSQuote(
                        symbol=symbol,
                        security_type=sec_type,
                        data=parsed,
                        raw=item,
                    ))
            return results

        return []
