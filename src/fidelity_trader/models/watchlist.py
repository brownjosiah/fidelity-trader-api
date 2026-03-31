from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class WatchlistSecurity(BaseModel):
    model_config = {"populate_by_name": True}

    symbol: str
    cusip: Optional[str] = None
    security_type: Optional[str] = Field(default=None, alias="securityType")
    news_state_ind: bool = Field(default=False, alias="newsStateInd")
    watch_closely_ind: bool = Field(default=False, alias="watchCloselyInd")
    rank_id: Optional[int] = Field(default=None, alias="rankId")
    security_id: Optional[str] = Field(default=None, alias="securityId")


class Watchlist(BaseModel):
    model_config = {"populate_by_name": True}

    watchlist_id: str = Field(alias="watchListId")
    watchlist_name: str = Field(alias="watchListName")
    watchlist_type_code: str = Field(alias="watchListTypeCode")
    is_default: bool = Field(default=False, alias="isDefault")
    sort_order: Optional[int] = Field(default=None, alias="sortOrder")
    created_timestamp: Optional[str] = Field(default=None, alias="createdTimeStamp")
    last_updated_time: Optional[str] = Field(default=None, alias="lastUpdatedTime")
    security_details: list[WatchlistSecurity] = Field(
        default_factory=list, alias="securityDetails"
    )


class WatchlistResponse(BaseModel):
    model_config = {"populate_by_name": True}

    watchlists: list[Watchlist] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "WatchlistResponse":
        """Parse the full API JSON response into a WatchlistResponse.

        Expected shape::

            {
                "sysMsgs": {...},
                "watchListDetails": [...]
            }
        """
        raw_lists = data.get("watchListDetails") or []
        return cls(
            watchlists=[Watchlist.model_validate(wl) for wl in raw_lists]
        )
