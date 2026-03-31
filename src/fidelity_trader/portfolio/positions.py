import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.position import PositionsResponse


class PositionsAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_positions(
        self,
        account_numbers: list[str],
        account_types: list[dict] = None,
    ) -> PositionsResponse:
        """Fetch positions for the given accounts.

        account_types: list of dicts with acctNum, acctType, acctSubType keys.
        If not provided, defaults to Brokerage type for all accounts.
        """
        if account_types is None:
            acct_details = [
                {
                    "retirementInd": False,
                    "tradable": False,
                    "acctNum": num,
                    "acctType": "Brokerage",
                    "acctSubType": "Brokerage",
                    "isTradable": True,
                    "managedAcctCode": None,
                    "filiSystem": None,
                    "filiProdDesc": None,
                    "filiProdCode": None,
                }
                for num in account_numbers
            ]
        else:
            acct_details = account_types

        body = {
            "request": {
                "parameter": {
                    "returnSecurityDetail": True,
                    "returnAvailabilityStatus": False,
                    "returnUnadjustedFields": True,
                    "returnPositionMarketValDetail": True,
                    "returnAccountGainLossDetail": True,
                    "returnPortfolioGainLossDetail": True,
                    "returnDistributionDetail": True,
                    "externalCustomerID": None,
                    "returnAdditionalPositionDetail": True,
                    "returnTradingAllowedActionDetail": True,
                    "returnSellToTransferEligible": False,
                    "returnBasketDetail": False,
                    "returnAccountBasketDetail": False,
                    "acctDetails": {"acctDetail": acct_details},
                }
            }
        }

        resp = self._http.post(f"{DPSERVICE_URL}/ftgw/dp/position/v2", json=body)
        resp.raise_for_status()
        return PositionsResponse.from_api_response(resp.json())
