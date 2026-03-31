"""MDDS WebSocket client for real-time market data streaming.

Connects to Fidelity's Market Data Distribution System via WebSocket.
Uses the session cookies from login for authentication.
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from fidelity_trader.streaming.mdds_fields import parse_fields, OPTION_FIELDS, EQUITY_FIELDS


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
    def is_option(self) -> bool:
        return self.security_type == "OP"


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

    def parse_message(self, raw: str) -> list[MDDSQuote]:
        """Parse a server message into quote updates.

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

        # Success response with data
        if data.get("ResponseType") == "1" and "Data" in data:
            quotes = []
            for item in data["Data"]:
                if item.get("0") != "success":
                    continue
                symbol = item.get("6", item.get("289", ""))
                sec_type = item.get("128", "")
                parsed = parse_fields(item)
                quotes.append(MDDSQuote(
                    symbol=symbol,
                    security_type=sec_type,
                    data=parsed,
                    raw=item,
                ))
            return quotes

        return []
