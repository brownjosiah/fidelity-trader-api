"""Order cancellation API, mirroring Fidelity Trader+ traffic."""
import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.cancel_order import CancelResponse

_CANCEL_PLACE_PATH = "/ftgw/dp/orderentry/cancel/place/v1"


class OrderCancelAPI:
    """Client for cancelling open orders.

    Usage::

        api = OrderCancelAPI(http_client)
        result = api.cancel_order(
            conf_num="24A0JX2V",
            acct_num="Z21772945",
            action_code="B",
        )
        assert result.is_accepted
    """

    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def cancel_order(
        self, conf_num: str, acct_num: str, action_code: str
    ) -> CancelResponse:
        """Cancel an open order.

        Args:
            conf_num: The confirmation number of the order to cancel.
            acct_num: The account number associated with the order.
            action_code: The original action code of the order (e.g. ``"B"`` for Buy).

        Returns:
            A :class:`~fidelity_trader.models.cancel_order.CancelResponse` with
            ``is_accepted == True`` when the cancellation is accepted.

        Raises:
            httpx.HTTPStatusError: if the server returns a non-2xx status.
        """
        body = {
            "request": {
                "parameter": {
                    "cancelOrderDetail": [
                        {
                            "confNum": conf_num,
                            "acctNum": acct_num,
                            "actionCode": action_code,
                        }
                    ],
                    "previewInd": False,
                    "confInd": False,
                }
            }
        }
        resp = self._http.post(f"{DPSERVICE_URL}{_CANCEL_PLACE_PATH}", json=body)
        resp.raise_for_status()
        return CancelResponse.from_api_response(resp.json())
