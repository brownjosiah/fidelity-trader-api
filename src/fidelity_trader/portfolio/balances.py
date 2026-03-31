import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.balance import BalancesResponse


class BalancesAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_balances(
        self,
        account_numbers: list[str],
        account_types: list[dict] = None,
    ) -> BalancesResponse:
        """Fetch balances for the given accounts.

        account_types: list of dicts with acctNum, acctType, acctSubType keys.
        If not provided, defaults to Brokerage type for all accounts.
        """
        if account_types is None:
            acct_details = [
                {
                    "acctType": "Brokerage",
                    "acctNum": num,
                    "acctSubType": "Brokerage",
                    "hardToBorrow": False,
                    "multiMarginSummaryInd": False,
                    "filiSystem": None,
                    "depositsInd": False,
                    "clientID": None,
                }
                for num in account_numbers
            ]
        else:
            acct_details = account_types

        body = {
            "request": {
                "parameter": {
                    "filters": {
                        "priceTiming": {
                            "includeRecent": True,
                            "includeIntraday": True,
                            "includeClose": True,
                        },
                        "requestedData": {
                            "includeAddlInfoDetail": True,
                            "includeAcctValDetail": True,
                            "includeAvailableToWithdrawDetail": True,
                            "includeCashDetail": True,
                            "includeBuyingPowerDetail": True,
                            "includeMarginDetail": True,
                            "includeBondDetail": True,
                            "includeShortDetail": True,
                            "includeOptionsDetail": True,
                            "includeSimplifiedMarginDetail": True,
                        },
                        "includeGrossLiquidityVal": False,
                        "includeDeposits": False,
                        "includeDCLoan": False,
                        "includeCryptoMarketVal": False,
                        "includeAvailForCryptoTransferDetail": False,
                    },
                    "acctDetails": {
                        "acctDetail": acct_details,
                    },
                }
            }
        }

        resp = self._http.post(f"{DPSERVICE_URL}/ftgw/dp/balance/detail/v2", json=body)
        resp.raise_for_status()
        return BalancesResponse.from_api_response(resp.json())
