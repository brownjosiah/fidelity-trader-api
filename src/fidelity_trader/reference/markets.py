import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.available_market import AvailableMarketsResponse


class AvailableMarketsAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_available_markets(
        self,
        symbol: str,
        account_numbers: list[str],
    ) -> AvailableMarketsResponse:
        """Fetch available trading markets for the given symbol and accounts."""
        body = {
            "symbol": symbol,
            "accounts": account_numbers,
            "requestType": "",
            "isCheckShares": False,
        }

        resp = self._http.post(
            f"{DPSERVICE_URL}/ftgw/dp/reference/security/stock/availablemarket/v1",
            json=body,
        )
        resp.raise_for_status()
        return AvailableMarketsResponse.from_api_response(resp.json())
