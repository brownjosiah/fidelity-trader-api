import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.loaned_securities import LoanedSecuritiesResponse


class LoanedSecuritiesAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_loaned_securities(
        self,
        account_numbers: list[str],
    ) -> LoanedSecuritiesResponse:
        """Fetch loaned securities data for the given accounts."""
        body = {
            "request": {
                "parameters": {
                    "acctDetails": [{"acctNum": num} for num in account_numbers],
                }
            }
        }

        resp = self._http.post(
            f"{DPSERVICE_URL}/ftgw/dp/retail-am-loanedsecurities/v1/accounts/positions/rates",
            json=body,
        )
        resp.raise_for_status()
        return LoanedSecuritiesResponse.from_api_response(resp.json())
