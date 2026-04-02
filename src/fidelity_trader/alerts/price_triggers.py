"""Price triggers list API — lists price-based alert triggers for a symbol."""
from __future__ import annotations

import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.price_trigger import PriceTriggersResponse

_PRICE_TRIGGERS_PATH = (
    "/ftgw/dp/retail-price-triggers/v1"
    "/investments/research/alert/price-triggers/list"
)


class PriceTriggersAPI:
    """Client for the Fidelity price triggers list endpoint."""

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_price_triggers(
        self,
        symbol: str,
        status: str = "active",
        offset: int = 0,
    ) -> PriceTriggersResponse:
        """Fetch the list of price triggers for a given symbol.

        GETs ``/ftgw/dp/retail-price-triggers/v1/investments/research/alert/
        price-triggers/list`` with query parameters ``symbol``, ``status``,
        and ``offset``.

        Args:
            symbol: Ticker symbol to query (e.g. ``"QS"``).
            status: Filter by trigger status (default ``"active"``).
            offset: Pagination offset (default ``0``).

        Returns:
            A :class:`~fidelity_trader.models.price_trigger.PriceTriggersResponse`.

        Raises:
            httpx.HTTPStatusError: on non-2xx responses.
        """
        params = {
            "symbol": symbol,
            "status": status,
            "offset": offset,
        }
        resp = self._http.get(
            f"{DPSERVICE_URL}{_PRICE_TRIGGERS_PATH}",
            params=params,
        )
        resp.raise_for_status()
        return PriceTriggersResponse.from_api_response(resp.json())
