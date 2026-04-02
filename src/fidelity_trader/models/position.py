from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from fidelity_trader.models._parsers import _parse_float, _parse_int


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class PriceDetail(BaseModel):
    model_config = {"populate_by_name": True}

    last_price: Optional[float] = Field(default=None, alias="lastPrice")
    last_price_chg: Optional[float] = Field(default=None, alias="lastPriceChg")
    last_price_chg_pct: Optional[float] = Field(default=None, alias="lastPriceChgPct")
    closing_price: Optional[float] = Field(default=None, alias="closingPrice")
    prev_close_price: Optional[float] = Field(default=None, alias="prevClosePrice")

    @field_validator(
        "last_price",
        "last_price_chg",
        "last_price_chg_pct",
        "closing_price",
        "prev_close_price",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class MarketValDetail(BaseModel):
    model_config = {"populate_by_name": True}

    market_val: Optional[float] = Field(default=None, alias="marketVal")
    previous_market_val: Optional[float] = Field(default=None, alias="previousMarketVal")
    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")
    total_gain_loss_pct: Optional[float] = Field(default=None, alias="totalGainLossPct")
    todays_gain_loss: Optional[float] = Field(default=None, alias="todaysGainLoss")
    todays_gain_loss_pct: Optional[float] = Field(default=None, alias="todaysGainLossPct")

    @field_validator(
        "market_val",
        "previous_market_val",
        "total_gain_loss",
        "total_gain_loss_pct",
        "todays_gain_loss",
        "todays_gain_loss_pct",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class CostBasisDetail(BaseModel):
    model_config = {"populate_by_name": True}

    avg_cost_per_share: Optional[float] = Field(default=None, alias="avgCostPerShare")
    cost_basis: Optional[float] = Field(default=None, alias="costBasis")

    @field_validator("avg_cost_per_share", "cost_basis", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class PositionDetail(BaseModel):
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    security_type: Optional[str] = Field(default=None, alias="securityType")
    security_sub_type: Optional[str] = Field(default=None, alias="securitySubType")
    security_description: Optional[str] = Field(default=None, alias="securityDescription")
    cusip: Optional[str] = None
    quantity: Optional[float] = None
    holding_pct: Optional[float] = Field(default=None, alias="holdingPct")
    price_detail: Optional[PriceDetail] = Field(default=None, alias="priceDetail")
    market_val_detail: Optional[MarketValDetail] = Field(default=None, alias="marketValDetail")
    cost_basis_detail: Optional[CostBasisDetail] = Field(default=None, alias="costBasisDetail")

    @field_validator("quantity", "holding_pct", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class AccountGainLossDetail(BaseModel):
    model_config = {"populate_by_name": True}

    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")
    total_gain_loss_pct: Optional[float] = Field(default=None, alias="totalGainLossPct")
    cost_basis_total: Optional[float] = Field(default=None, alias="costBasisTotal")
    account_market_val: Optional[float] = Field(default=None, alias="accountMarketVal")
    todays_gain_loss: Optional[float] = Field(default=None, alias="todaysGainLoss")
    todays_gain_loss_pct: Optional[float] = Field(default=None, alias="todaysGainLossPct")

    @field_validator(
        "total_gain_loss",
        "total_gain_loss_pct",
        "cost_basis_total",
        "account_market_val",
        "todays_gain_loss",
        "todays_gain_loss_pct",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class AccountPositionDetail(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    account_position_count: int = Field(alias="accountPositionCount")
    account_gain_loss_detail: Optional[AccountGainLossDetail] = Field(
        default=None, alias="accountGainLossDetail"
    )
    positions: list[PositionDetail] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _extract_positions(cls, data: Any) -> Any:
        """Flatten positionDetails.positionDetail[] into positions."""
        if not isinstance(data, dict):
            return data
        if "positions" not in data:
            pos_details = data.get("positionDetails") or {}
            pos_list = pos_details.get("positionDetail") or []
            data = dict(data)
            data["positions"] = pos_list
        return data


class PortfolioGainLossDetail(BaseModel):
    model_config = {"populate_by_name": True}

    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")
    total_gain_loss_pct: Optional[float] = Field(default=None, alias="totalGainLossPct")
    cost_basis_total: Optional[float] = Field(default=None, alias="costBasisTotal")
    portfolio_total_val: Optional[float] = Field(default=None, alias="portfolioTotalVal")
    todays_gain_loss: Optional[float] = Field(default=None, alias="todaysGainLoss")
    todays_gain_loss_pct: Optional[float] = Field(default=None, alias="todaysGainLossPct")

    @field_validator(
        "total_gain_loss",
        "total_gain_loss_pct",
        "cost_basis_total",
        "portfolio_total_val",
        "todays_gain_loss",
        "todays_gain_loss_pct",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class PortfolioDetail(BaseModel):
    model_config = {"populate_by_name": True}

    portfolio_position_count: int = Field(alias="portfolioPositionCount")
    portfolio_gain_loss_detail: Optional[PortfolioGainLossDetail] = Field(
        default=None, alias="portfolioGainLossDetail"
    )


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class PositionsResponse(BaseModel):
    model_config = {"populate_by_name": True}

    portfolio_detail: Optional[PortfolioDetail] = None
    accounts: list[AccountPositionDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "PositionsResponse":
        """Parse the full API JSON response into a PositionsResponse.

        Expected shape::

            {
                "position": {
                    "portfolioDetail": {...},
                    "acctDetails": {
                        "acctDetail": [...]
                    }
                }
            }
        """
        position = data.get("position") or {}
        portfolio_detail = position.get("portfolioDetail")
        acct_list = (position.get("acctDetails") or {}).get("acctDetail") or []
        return cls(
            portfolio_detail=PortfolioDetail.model_validate(portfolio_detail)
            if portfolio_detail
            else None,
            accounts=[AccountPositionDetail.model_validate(a) for a in acct_list],
        )
