import httpx

from fidelity_trader._http import DPSERVICE_URL, make_req_id
from fidelity_trader.models.research import EarningsResponse, DividendsResponse

_EARNINGS_PATH = "/ftgw/dpdirect/research/earning/v1"
_DIVIDENDS_PATH = "/ftgw/dpdirect/research/dividend/v1"


class ResearchAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_earnings(self, symbols: list[str]) -> EarningsResponse:
        """Fetch earnings data for the given symbols.

        Symbols are pipe-delimited in the fvSymbol query parameter, matching
        the request format observed in captured Trader+ traffic.
        """
        params = {"fvSymbol": "|".join(symbols)}
        headers = {"fsreqid": make_req_id()}
        resp = self._http.get(
            f"{DPSERVICE_URL}{_EARNINGS_PATH}",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        return EarningsResponse.from_api_response(resp.json())

    def get_dividends(self, symbols: list[str]) -> DividendsResponse:
        """Fetch dividend data for the given symbols.

        Symbols are pipe-delimited in the fvSymbol query parameter, matching
        the request format observed in captured Trader+ traffic.
        """
        params = {"fvSymbol": "|".join(symbols)}
        headers = {"fsreqid": make_req_id()}
        resp = self._http.get(
            f"{DPSERVICE_URL}{_DIVIDENDS_PATH}",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        return DividendsResponse.from_api_response(resp.json())
