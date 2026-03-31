"""Historical chart data API client for the fastquote endpoint.

Endpoint:
  GET https://fastquote.fidelity.com/service/marketdata/historical/chart/json

The response is JSONP-wrapped; this module generates the callback name,
strips the wrapper, and parses the inner JSON into typed models.

Traffic captured from Fidelity Trader+ desktop application.
"""

from __future__ import annotations

import json
import re
import time

import httpx

from fidelity_trader._http import FASTQUOTE_URL
from fidelity_trader.models.chart import ChartResponse

_CHART_PATH = "/service/marketdata/historical/chart/json"

# JSONP wrapper pattern: callback_name( ... )
_JSONP_RE = re.compile(r"^\w+\((.+)\)\s*$", re.DOTALL)


def _make_callback() -> str:
    """Generate a JSONP callback name matching the pattern used by Trader+."""
    ts = int(time.time() * 1000)
    return f"jsonp_{ts}_1"


def _unwrap_jsonp(text: str, callback: str) -> dict:
    """Strip the JSONP wrapper and parse the inner JSON."""
    stripped = text.strip()
    # Try exact prefix/suffix first for speed
    prefix = f"{callback}("
    if stripped.startswith(prefix) and stripped.endswith(")"):
        inner = stripped[len(prefix):-1]
        return json.loads(inner)
    # Fall back to regex for slight variations
    m = _JSONP_RE.match(stripped)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"Response does not look like JSONP: {stripped[:120]!r}")


class ChartAPI:
    """Client for the historical chart data endpoint on fastquote.fidelity.com."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_chart(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        bar_width: str = "5",
        extended_hours: bool = True,
    ) -> ChartResponse:
        """Fetch historical OHLCV bar data for *symbol*.

        Parameters
        ----------
        symbol:
            Ticker symbol, e.g. ``"SPY"``.
        start_date:
            Start of the requested range as ``"YYYY/MM/DD-HH:MM:SS"``.
        end_date:
            End of the requested range as ``"YYYY/MM/DD-HH:MM:SS"``.
        bar_width:
            Bar size. One of ``"1"``, ``"5"``, ``"15"``, ``"30"``, ``"60"``,
            ``"D"``, ``"W"``, ``"M"``. Defaults to ``"5"`` (5-minute bars).
        extended_hours:
            Include pre/post-market bars when ``True`` (sends ``extendedHours=Y``).

        Returns
        -------
        ChartResponse
            Parsed symbol info and list of OHLCV bars.
        """
        callback = _make_callback()
        params = {
            "callback": callback,
            "symbols": symbol,
            "startDate": start_date,
            "endDate": end_date,
            "barWidth": bar_width,
            "corpActions": "Y",
            "timestamp": "start",
            "extendedHours": "Y" if extended_hours else "N",
            "isInitialFetch": "true",
            "productid": "atn",
            "quoteType": "R",
        }
        resp = self._http.get(
            f"{FASTQUOTE_URL}{_CHART_PATH}",
            params=params,
        )
        resp.raise_for_status()
        data = _unwrap_jsonp(resp.text, callback)
        return ChartResponse.from_dict(data)
