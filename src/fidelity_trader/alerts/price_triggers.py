"""Price triggers API — list, create, and delete price-based alert triggers."""
from __future__ import annotations

from typing import List, Optional

import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.price_trigger import (
    DEFAULT_DEVICES,
    PriceTriggerCreateRequest,
    PriceTriggerCreateResponse,
    PriceTriggerDeleteRequest,
    PriceTriggerDeleteResponse,
    PriceTriggerDevice,
    PriceTriggersResponse,
)

_PRICE_TRIGGERS_BASE = (
    "/ftgw/dp/retail-price-triggers/v1"
    "/investments/research/alert/price-triggers"
)

_PRICE_TRIGGERS_PATH = f"{_PRICE_TRIGGERS_BASE}/list"
_PRICE_TRIGGERS_CREATE_PATH = f"{_PRICE_TRIGGERS_BASE}/create"
_PRICE_TRIGGERS_DELETE_PATH = f"{_PRICE_TRIGGERS_BASE}/delete"


class PriceTriggersAPI:
    """Client for the Fidelity price triggers endpoints (list, create, delete)."""

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

    def create_price_trigger(
        self,
        symbol: str,
        operator: str,
        value: float,
        currency: str = "USD",
        notes: str = "",
        devices: Optional[List[PriceTriggerDevice]] = None,
    ) -> PriceTriggerCreateResponse:
        """Create a new price trigger.

        POSTs to ``/ftgw/dp/retail-price-triggers/v1/investments/research/
        alert/price-triggers/create``.

        Args:
            symbol: Ticker symbol (e.g. ``"SPY"``).
            operator: Trigger operator. Captured values:
                ``"lessThanPercent"``, ``"greaterThanPercent"``,
                ``"lessThan"``, ``"greaterThan"``.
            value: Trigger threshold value.
            currency: Currency code (default ``"USD"``).
            notes: Optional note text (default ``""``).
            devices: Notification devices. Defaults to
                Active Trader Pro and Fidelity mobile applications.

        Returns:
            A :class:`~fidelity_trader.models.price_trigger.PriceTriggerCreateResponse`.

        Raises:
            httpx.HTTPStatusError: on non-2xx responses.
        """
        request = PriceTriggerCreateRequest(
            symbol=symbol,
            operator=operator,
            value=value,
            currency=currency,
            notes=notes,
            devices=devices if devices is not None else list(DEFAULT_DEVICES),
        )
        resp = self._http.post(
            f"{DPSERVICE_URL}{_PRICE_TRIGGERS_CREATE_PATH}",
            json=request.to_api_payload(),
        )
        resp.raise_for_status()
        return PriceTriggerCreateResponse.from_api_response(resp.json())

    def delete_price_triggers(
        self,
        trigger_ids: List[str],
    ) -> PriceTriggerDeleteResponse:
        """Delete one or more price triggers by ID.

        POSTs to ``/ftgw/dp/retail-price-triggers/v1/investments/research/
        alert/price-triggers/delete``.

        Args:
            trigger_ids: List of trigger ID strings to delete.

        Returns:
            A :class:`~fidelity_trader.models.price_trigger.PriceTriggerDeleteResponse`.

        Raises:
            httpx.HTTPStatusError: on non-2xx responses.
        """
        request = PriceTriggerDeleteRequest(trigger_ids=trigger_ids)
        resp = self._http.post(
            f"{DPSERVICE_URL}{_PRICE_TRIGGERS_DELETE_PATH}",
            json=request.to_api_payload(),
        )
        resp.raise_for_status()
        return PriceTriggerDeleteResponse.from_api_response(resp.json())
