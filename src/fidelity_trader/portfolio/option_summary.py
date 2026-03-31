import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.option_summary import OptionSummaryResponse


class OptionSummaryAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_option_summary(
        self,
        account_numbers: list[str],
    ) -> OptionSummaryResponse:
        """Fetch option positions summary for the given accounts."""
        body = {
            "request": {
                "parameter": {
                    "returnCostBasisDetails": True,
                    "returnIntradayDetails": True,
                    "view": "EXPIRATION",
                    "returnUnpairedPositions": True,
                    "acctDetails": {
                        "acctDetail": [
                            {"acctNum": num} for num in account_numbers
                        ]
                    },
                }
            }
        }

        resp = self._http.post(
            f"{DPSERVICE_URL}/ftgw/dp/retail-am-optionsummary/v1/accounts/positions/option-summary/get",
            json=body,
        )
        resp.raise_for_status()
        return OptionSummaryResponse.from_api_response(resp.json())
