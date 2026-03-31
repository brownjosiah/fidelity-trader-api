from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class MarketHours(BaseModel):
    model_config = {"populate_by_name": True}

    market_opening_hours: str = Field(alias="marketOpeningHours")
    market_closing_hours: str = Field(alias="marketClosingHours")
    short_sell_opening_hours: str = Field(alias="shortSellOpeningHours")
    short_sell_closing_hours: str = Field(alias="shortSellClosingHours")
    market_order_opening_hours: str = Field(alias="marketOrderOpeningHours")
    market_order_closing_hours: str = Field(alias="marketOrderClosingHours")
    market_order_accept_from_hours: str = Field(alias="marketOrderAcceptFromHours")
    market_order_accept_to_hours: str = Field(alias="marketOrderAcceptToHours")


class OrderTypeSupported(BaseModel):
    model_config = {"populate_by_name": True}

    fill_or_kill_ind: bool = Field(alias="fillOrKillInd")
    immediate_or_cancel_ind: bool = Field(alias="immediateOrCancelInd")
    all_or_none_ind: bool = Field(alias="allOrNoneInd")
    not_held_ind: bool = Field(alias="notHeldInd")
    do_not_reduce_ind: bool = Field(alias="doNotReduceInd")
    cash_settle_ind: bool = Field(alias="cashSettleInd")
    next_day_ind: bool = Field(alias="nextDayInd")
    stop_limit_ind: bool = Field(alias="stopLimitInd")
    short_sell_ind: bool = Field(alias="shortSellInd")
    pegged_ind: bool = Field(alias="peggedInd")
    discretion_ind: bool = Field(alias="discretionInd")
    limit_ind: bool = Field(alias="limitInd")
    market_ind: bool = Field(alias="marketInd")
    trail_limit_ind: bool = Field(alias="trailLimitInd")
    trail_stop_ind: bool = Field(alias="trailStopInd")
    cancel_replace_ind: bool = Field(alias="cancelReplaceInd")
    hidden_ind: bool = Field(alias="hiddenInd")
    regular_session_ind: bool = Field(alias="regularSessionInd")
    pre_market_session_ind: bool = Field(alias="preMarketSessionInd")
    after_hours_session_ind: bool = Field(alias="afterHoursSessionInd")


class AvailableMarket(BaseModel):
    model_config = {"populate_by_name": True}

    marketplace: str
    routing_code: str = Field(alias="routingCode")
    name: str
    exchange_symbol: Optional[str] = Field(default=None, alias="exchangeSymbol")
    market_hours: MarketHours = Field(alias="marketHours")
    order_type_supported: OrderTypeSupported = Field(alias="orderTypeSupported")
    display_quantity_min: str = Field(alias="displayQuantityMin")


class SecurityInfo(BaseModel):
    model_config = {"populate_by_name": True}

    symbol: str
    avail_mkt_cnt: int = Field(alias="availMktCnt")
    avail_shares: Optional[float] = Field(default=None, alias="availShares")
    cusip: str


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class AvailableMarketsResponse(BaseModel):
    model_config = {"populate_by_name": True}

    security: SecurityInfo
    available_markets: list[AvailableMarket] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "AvailableMarketsResponse":
        """Parse the full API JSON response into an AvailableMarketsResponse.

        Expected shape::

            {
                "security": {...},
                "availableMarkets": [...]
            }
        """
        security_data = data.get("security") or {}
        markets_list = data.get("availableMarkets") or []
        return cls(
            security=SecurityInfo.model_validate(security_data),
            available_markets=[AvailableMarket.model_validate(m) for m in markets_list],
        )
