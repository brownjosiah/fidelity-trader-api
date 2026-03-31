import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.watchlist import WatchlistResponse

_WATCHLIST_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/retail-watchlist/v1/customers/watchlists/get"
)


class WatchlistAPI:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def get_watchlists(
        self,
        watchlist_ids: list[str] = None,
        watchlist_type_code: str = "WL",
        include_security_details: bool = True,
        position_types: list[str] = None,
    ) -> WatchlistResponse:
        """Fetch all watchlists for the authenticated customer.

        watchlist_ids: list of specific watchlist UUIDs to retrieve; pass
            an empty list (or None) to retrieve all watchlists.
        watchlist_type_code: watchlist type, typically "WL".
        include_security_details: whether to include per-security metadata.
        position_types: position type filters, e.g. ["H", "O"].
        """
        if watchlist_ids is None:
            watchlist_ids = []
        if position_types is None:
            position_types = ["H", "O"]

        body = {
            "watchlists": [
                {
                    "watchListIds": watchlist_ids,
                    "watchListTypeCode": watchlist_type_code,
                }
            ],
            "includeWatchListSecurityDetails": include_security_details,
            "positionTypes": position_types,
        }

        resp = self._http.post(_WATCHLIST_URL, json=body)
        resp.raise_for_status()
        return WatchlistResponse.from_api_response(resp.json())
