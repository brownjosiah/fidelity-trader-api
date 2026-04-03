"""Single-leg option order preview and place API, mirroring Fidelity Trader+ traffic."""
import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.exceptions import DryRunError
from fidelity_trader.models.single_option_order import (
    SingleOptionOrderRequest,
    SingleOptionPreviewResponse,
    SingleOptionPlaceResponse,
)

_OPTION_PREVIEW_PATH = "/ftgw/dp/orderentry/option/preview/v2"
_OPTION_PLACE_PATH = "/ftgw/dp/orderentry/option/place/v2"


class SingleOptionOrderAPI:
    """Client for single-leg option order preview and placement.

    Workflow:
        1. Call ``preview_order()`` to validate the order and obtain a ``confNum``.
        2. Pass that ``confNum`` to ``place_order()`` to submit the order.

    Captured from Fidelity Trader+ traffic against:
        ``POST https://dpservice.fidelity.com/ftgw/dp/orderentry/option/preview/v2``
        ``POST https://dpservice.fidelity.com/ftgw/dp/orderentry/option/place/v2``
    """

    def __init__(self, http: httpx.Client, live_trading: bool = False) -> None:
        self._http = http
        self._live_trading = live_trading

    def preview_order(
        self, order: SingleOptionOrderRequest
    ) -> SingleOptionPreviewResponse:
        """Preview a single-leg option order.

        POSTs to the option preview endpoint with the request body derived from
        *order* and returns a parsed :class:`SingleOptionPreviewResponse`.  The
        ``confNum`` on the response must be supplied to :meth:`place_order`.

        Raises:
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        body = order.to_preview_body()
        resp = self._http.post(f"{DPSERVICE_URL}{_OPTION_PREVIEW_PATH}", json=body)
        resp.raise_for_status()
        return SingleOptionPreviewResponse.from_api_response(resp.json())

    def place_order(
        self, order: SingleOptionOrderRequest, conf_num: str
    ) -> SingleOptionPlaceResponse:
        """Place a previously-previewed single-leg option order.

        *conf_num* must be the ``confNum`` returned by :meth:`preview_order`.
        Returns a parsed :class:`SingleOptionPlaceResponse` with
        ``respTypeCode="A"`` when the order is accepted.

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
        resp = self._http.post(f"{DPSERVICE_URL}{_OPTION_PLACE_PATH}", json=body)
        resp.raise_for_status()
        return SingleOptionPlaceResponse.from_api_response(resp.json())
