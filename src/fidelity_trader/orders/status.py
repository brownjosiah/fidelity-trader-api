import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.order import OrderStatusResponse

_ORDER_STATUS_PATH = "/ftgw/dp/retail-order-status/v3/accounts/orders/status-summary"


class OrderStatusAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_order_status(self, account_numbers: list[str]) -> OrderStatusResponse:
        """Fetch order status summary for the given account numbers.

        Builds the exact request body shape observed in captured Trader+ traffic
        and POSTs to the retail-order-status v3 endpoint.
        """
        acct_details = [
            {"acctNum": num, "accType": None}
            for num in account_numbers
        ]

        body = {
            "request": {
                "parameter": {
                    "fbOpenInd": None,
                    "fbUSDInd": None,
                    "fbFigurationInd": None,
                    "fbDisbursementInd": None,
                    "fbIncludeOptionInd": None,
                    "fbPriceImprovementInd": None,
                    "fvOrderStatusType": None,
                    "fvSymbolWithOption": None,
                    "fvExecCode": None,
                    "fvSymbol": None,
                    "fvOrderTypeCode": None,
                    "orderId": None,
                    "symbolOptIndCode": None,
                    "acctDetails": {
                        "acctDetail": acct_details,
                    },
                }
            }
        }

        resp = self._http.post(f"{DPSERVICE_URL}{_ORDER_STATUS_PATH}", json=body)
        resp.raise_for_status()
        return OrderStatusResponse.from_api_response(resp.json())
