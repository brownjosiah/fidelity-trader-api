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


# ---------------------------------------------------------------------------
# Save watchlist models (from captured POST .../watchlists/save traffic)
# ---------------------------------------------------------------------------


class SysMsg(BaseModel):
    """Single system message from the Fidelity API response."""
    model_config = {"populate_by_name": True}

    message: str = ""
    detail: str = ""
    source: str = ""
    code: str = ""
    type: str = ""


class SavedSecurity(BaseModel):
    """Security entry returned in the save-watchlist response."""
    model_config = {"populate_by_name": True}

    security_id: str = Field(alias="securityId")
    rank_id: int = Field(alias="rankId")
    symbol: str


class SavedWatchlist(BaseModel):
    """Single watchlist entry returned in the save-watchlist response."""
    model_config = {"populate_by_name": True}

    watchlist_id: str = Field(alias="watchListId")
    security_details: list[SavedSecurity] = Field(
        default_factory=list, alias="securityDetails"
    )


class WatchlistSaveResponse(BaseModel):
    """Parsed response from ``POST .../watchlists/save``.

    Expected shape::

        {
            "sysMsgs": { "sysMsg": [ { "message": "...", "code": "2000", ... } ] },
            "watchListDetails": [ { "watchListId": "...", "securityDetails": [...] } ]
        }
    """
    model_config = {"populate_by_name": True}

    sys_msgs: list[SysMsg] = Field(default_factory=list)
    watchlist_details: list[SavedWatchlist] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "WatchlistSaveResponse":
        raw_msgs = (data.get("sysMsgs") or {}).get("sysMsg") or []
        raw_watchlists = data.get("watchListDetails") or []
        return cls(
            sys_msgs=[SysMsg.model_validate(m) for m in raw_msgs],
            watchlist_details=[
                SavedWatchlist.model_validate(wl) for wl in raw_watchlists
            ],
        )

    @property
    def is_success(self) -> bool:
        """Return True when the API reports success (code ``"2000"``)."""
        return any(m.code == "2000" for m in self.sys_msgs)
