"""Multi-leg option order preview and place API, mirroring Fidelity Trader+ traffic."""
import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.option_order import (
    MultiLegOptionOrderRequest,
    MultiLegOptionPreviewResponse,
    MultiLegOptionPlaceResponse,
)

_MULTILEGOPTION_PREVIEW_PATH = "/ftgw/dp/orderentry/multilegoption/preview/v1"
_MULTILEGOPTION_PLACE_PATH = "/ftgw/dp/orderentry/multilegoption/place/v1"


class MultiLegOptionOrderAPI:
    """Client for multi-leg option order preview and placement.

    Workflow:
        1. Call ``preview_order()`` to validate the order and obtain a ``confNum``.
        2. Pass that ``confNum`` to ``place_order()`` to submit the order.

    Captured from Fidelity Trader+ traffic against:
        ``POST https://dpservice.fidelity.com/ftgw/dp/orderentry/multilegoption/preview/v1``
        ``POST https://dpservice.fidelity.com/ftgw/dp/orderentry/multilegoption/place/v1``
    """

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def preview_order(
        self, order: MultiLegOptionOrderRequest
    ) -> MultiLegOptionPreviewResponse:
        """Preview a multi-leg option order.

        POSTs to the multilegoption preview endpoint with the request body derived
        from *order* and returns a parsed :class:`MultiLegOptionPreviewResponse`.
        The ``confNum`` on the response must be supplied to :meth:`place_order`.

        Raises:
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        body = order.to_preview_body()
        resp = self._http.post(
            f"{DPSERVICE_URL}{_MULTILEGOPTION_PREVIEW_PATH}", json=body
        )
        resp.raise_for_status()
        return MultiLegOptionPreviewResponse.from_api_response(resp.json())

    def place_order(
        self, order: MultiLegOptionOrderRequest, conf_num: str
    ) -> MultiLegOptionPlaceResponse:
        """Place a previously-previewed multi-leg option order.

        *conf_num* must be the ``confNum`` returned by :meth:`preview_order`.
        Returns a parsed :class:`MultiLegOptionPlaceResponse` with
        ``respTypeCode="A"`` when the order is accepted.

        Raises:
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        body = order.to_place_body(conf_num)
        resp = self._http.post(
            f"{DPSERVICE_URL}{_MULTILEGOPTION_PLACE_PATH}", json=body
        )
        resp.raise_for_status()
        return MultiLegOptionPlaceResponse.from_api_response(resp.json())
