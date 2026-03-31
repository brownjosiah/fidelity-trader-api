import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.account_detail import AccountsResponse


class AccountsAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def discover_accounts(
        self,
        categories: str = "Brokerage,WorkplaceContributions",
    ) -> AccountsResponse:
        """Discover all accounts for the authenticated user.

        Calls the v2 account discovery endpoint with the standard filter set
        from captured Trader+ traffic.
        """
        body = {
            "acctCategory": categories,
            "filters": {
                "returnPreferenceDetail": True,
                "returnAcctTradeAttrDetail": True,
                "returnAcctTypesIndDetail": True,
                "returnAcctLegalAttrDetail": True,
                "returnWorkplacePlanDetail": True,
                "returnGroupDetail": True,
            },
        }

        resp = self._http.post(
            f"{DPSERVICE_URL}/ftgw/dp/customer-am-acctnxt/v2/accounts",
            json=body,
        )
        resp.raise_for_status()
        return AccountsResponse.from_api_response(resp.json())

    def get_account_features(self, account_numbers: list[str]) -> dict:
        """Fetch feature flags for the given account numbers.

        Passthrough to the v2 account features endpoint. Returns the raw
        response dict from the API.
        """
        body = {"acctNums": account_numbers}

        resp = self._http.post(
            f"{DPSERVICE_URL}/ftgw/dp/customer-am-feature/v2/accounts/features/get",
            json=body,
        )
        resp.raise_for_status()
        return resp.json()
