from __future__ import annotations

from typing import Union

import httpx

from fidelity_trader._http import DPSERVICE_URL
from fidelity_trader.models.watchlist import WatchlistResponse, WatchlistSaveResponse

_WATCHLIST_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/retail-watchlist/v1/customers/watchlists/get"
)
_WATCHLIST_SAVE_URL = (
    f"{DPSERVICE_URL}/ftgw/dp/retail-watchlist/v1/customers/watchlists/save"
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

    def save_watchlist(
        self,
        watchlist_details: Union[dict, list[dict]],
    ) -> WatchlistSaveResponse:
        """Save (create or update) one or more watchlists.

        watchlist_details: Either a single watchlist dict or a list of
            watchlist dicts matching the ``watchListDetails`` shape from
            the captured traffic::

                {
                    "watchListName": "Buys",
                    "productCode": "WL",
                    "isDefault": true,
                    "watchListId": "uuid-here",
                    "watchListTypeCode": "WL",
                    "securityDetails": [
                        { "symbol": "ES", "shareQuantity": "0", ... },
                    ]
                }

            When a single dict is passed it is automatically wrapped in a
            list for the ``watchListDetails`` array.
        """
        if isinstance(watchlist_details, dict):
            watchlist_details = [watchlist_details]

        body = {"watchListDetails": watchlist_details}

        resp = self._http.post(_WATCHLIST_SAVE_URL, json=body)
        resp.raise_for_status()
        return WatchlistSaveResponse.from_api_response(resp.json())
