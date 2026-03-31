"""Equity order preview and place API, mirroring Fidelity Trader+ traffic."""
import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.equity_order import (
    EquityOrderRequest,
    EquityPreviewResponse,
    EquityPlaceResponse,
)

_EQUITY_PREVIEW_PATH = "/ftgw/dp/orderentry/equity/preview/v1"
_EQUITY_PLACE_PATH = "/ftgw/dp/orderentry/equity/place/v1"


class EquityOrderAPI:
    """Client for equity order preview and placement.

    Workflow:
        1. Call ``preview_order()`` to validate the order and obtain a ``confNum``.
        2. Pass that ``confNum`` to ``place_order()`` to submit the order.
    """

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def preview_order(self, order: EquityOrderRequest) -> EquityPreviewResponse:
        """Preview an equity order.

        POSTs to the equity preview endpoint with the request body derived from
        *order* and returns a parsed :class:`EquityPreviewResponse`.  The
        ``confNum`` on the response must be supplied to :meth:`place_order`.

        Raises:
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        body = order.to_preview_body()
        resp = self._http.post(f"{DPSERVICE_URL}{_EQUITY_PREVIEW_PATH}", json=body)
        resp.raise_for_status()
        return EquityPreviewResponse.from_api_response(resp.json())

    def place_order(
        self, order: EquityOrderRequest, conf_num: str
    ) -> EquityPlaceResponse:
        """Place a previously-previewed equity order.

        *conf_num* must be the ``confNum`` returned by :meth:`preview_order`.
        Returns a parsed :class:`EquityPlaceResponse` with ``respTypeCode="A"``
        when the order is accepted.

        Raises:
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        body = order.to_place_body(conf_num)
        resp = self._http.post(f"{DPSERVICE_URL}{_EQUITY_PLACE_PATH}", json=body)
        resp.raise_for_status()
        return EquityPlaceResponse.from_api_response(resp.json())
