"""Conditional order (OTOCO/OTO/OCO) preview and place API, mirroring Fidelity Trader+ traffic."""
import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.exceptions import DryRunError
from fidelity_trader.models.conditional_order import (
    ConditionalOrderRequest,
    ConditionalPreviewResponse,
    ConditionalPlaceResponse,
)

_COND_PREVIEW_PATH = "/ftgw/dp/orderentry/conditional/preview/v1"
_COND_PLACE_PATH = "/ftgw/dp/orderentry/conditional/place/v1"


class ConditionalOrderAPI:
    """Client for conditional order preview and placement.

    Supports OTOCO, OTO, and OCO conditional order types.

    Workflow:
        1. Call ``preview_order()`` to validate all legs and obtain confNums.
        2. Pass those confNums to ``place_order()`` to submit the conditional order.
           The confNums are applied to triggered legs only (index >= 1).
    """

    def __init__(self, http: httpx.Client, live_trading: bool = False) -> None:
        self._http = http
        self._live_trading = live_trading

    def preview_order(
        self, order: ConditionalOrderRequest
    ) -> ConditionalPreviewResponse:
        """Preview a conditional order.

        POSTs to the conditional preview endpoint with the request body derived
        from *order* and returns a parsed :class:`ConditionalPreviewResponse`.
        The ``conf_nums`` on the response must be supplied to :meth:`place_order`.

        Raises:
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        body = order.to_preview_body()
        resp = self._http.post(f"{DPSERVICE_URL}{_COND_PREVIEW_PATH}", json=body)
        resp.raise_for_status()
        return ConditionalPreviewResponse.from_api_response(resp.json())

    def place_order(
        self, order: ConditionalOrderRequest, conf_nums: list[str]
    ) -> ConditionalPlaceResponse:
        """Place a previously-previewed conditional order.

        *conf_nums* must be the confirmation numbers returned by
        :meth:`preview_order`.  They are applied to triggered legs only
        (the primary leg at index 0 does not receive a confNum).

        Returns a parsed :class:`ConditionalPlaceResponse` with
        ``respTypeCode="A"`` for each leg when the order is accepted.

        Raises:
            DryRunError: if dry-run mode is active.
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        if not self._live_trading:
            raise DryRunError(
                "Order placement blocked — dry-run mode is active. "
                "Pass live_trading=True to FidelityClient or set "
                "FIDELITY_LIVE_TRADING=true to enable live trading."
            )
        body = order.to_place_body(conf_nums)
        resp = self._http.post(f"{DPSERVICE_URL}{_COND_PLACE_PATH}", json=body)
        resp.raise_for_status()
        return ConditionalPlaceResponse.from_api_response(resp.json())
