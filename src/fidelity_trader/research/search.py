import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.search import AutosuggestResponse

_AUTOSUGGEST_PATH = "/ftgw/dpdirect/search/autosuggest/v1"


class SearchAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def autosuggest(self, query: str) -> AutosuggestResponse:
        """Fetch symbol autosuggest results for the given query string.

        Uses the GET autosuggest endpoint observed in captured Trader+ traffic,
        passing the query as the `q` parameter.
        """
        params = {"q": query}
        resp = self._http.get(
            f"{DPSERVICE_URL}{_AUTOSUGGEST_PATH}",
            params=params,
        )
        resp.raise_for_status()
        return AutosuggestResponse.from_api_response(resp.json())
