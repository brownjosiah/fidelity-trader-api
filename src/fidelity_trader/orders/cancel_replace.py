"""Cancel-and-replace (order modification) API, mirroring Fidelity Trader+ traffic."""
import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.exceptions import DryRunError
from fidelity_trader.models.cancel_replace import (
    CancelReplaceRequest,
    CancelReplacePreviewResponse,
    CancelReplacePlaceResponse,
)

_CR_PREVIEW_PATH = "/ftgw/dp/orderentry/cancelandreplace/preview/v1"
_CR_PLACE_PATH = "/ftgw/dp/orderentry/cancelandreplace/place/v1"


class CancelReplaceAPI:
    """Client for cancel-and-replace (order modification) preview and placement.

    Workflow:
        1. Call ``preview_order()`` to validate the modification and obtain a ``confNum``.
        2. Pass that ``confNum`` to ``place_order()`` to submit the modified order.
    """

    def __init__(self, http: httpx.Client, live_trading: bool = False) -> None:
        self._http = http
        self._live_trading = live_trading

    def preview_order(
        self, order: CancelReplaceRequest
    ) -> CancelReplacePreviewResponse:
        """Preview a cancel-and-replace order modification.

        POSTs to the cancel-and-replace preview endpoint with the request body
        derived from *order* and returns a parsed
        :class:`CancelReplacePreviewResponse`.  The ``confNum`` on the response
        must be supplied to :meth:`place_order`.

        Raises:
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        body = order.to_preview_body()
        resp = self._http.post(f"{DPSERVICE_URL}{_CR_PREVIEW_PATH}", json=body)
        resp.raise_for_status()
        return CancelReplacePreviewResponse.from_api_response(resp.json())

    def place_order(
        self, order: CancelReplaceRequest, conf_num: str
    ) -> CancelReplacePlaceResponse:
        """Place a previously-previewed cancel-and-replace order modification.

        *conf_num* must be the ``confNum`` returned by :meth:`preview_order`.
        Returns a parsed :class:`CancelReplacePlaceResponse` with
        ``respTypeCode="A"`` when the modification is accepted.

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
        body = order.to_place_body(conf_num)
        resp = self._http.post(f"{DPSERVICE_URL}{_CR_PLACE_PATH}", json=body)
        resp.raise_for_status()
        return CancelReplacePlaceResponse.from_api_response(resp.json())
