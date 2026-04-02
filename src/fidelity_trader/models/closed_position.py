from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from fidelity_trader.models._parsers import _parse_float


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class WashUnadjustedGainLossDetail(BaseModel):
    model_config = {"populate_by_name": True}

    unadjusted_gain: Optional[float] = Field(default=None, alias="unadjustedGain")
    unadjusted_loss: Optional[float] = Field(default=None, alias="unadjustedLoss")
    unadjusted_total_gain_loss: Optional[float] = Field(
        default=None, alias="unadjustedTotalGainLoss"
    )

    @field_validator(
        "unadjusted_gain",
        "unadjusted_loss",
        "unadjusted_total_gain_loss",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class GainLossDetail(BaseModel):
    model_config = {"populate_by_name": True}

    realized_gain: Optional[float] = Field(default=None, alias="realizedGain")
    realized_loss: Optional[float] = Field(default=None, alias="realizedLoss")
    disallowed_loss: Optional[float] = Field(default=None, alias="disallowedLoss")
    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")
    unadjusted_total_gain_loss: Optional[float] = Field(
        default=None, alias="unadjustedTotalGainLoss"
    )
    wash_unadjusted_gain_loss_detail: Optional[WashUnadjustedGainLossDetail] = Field(
        default=None, alias="washUnadjustedGainLossDetail"
    )

    @field_validator(
        "realized_gain",
        "realized_loss",
        "disallowed_loss",
        "total_gain_loss",
        "unadjusted_total_gain_loss",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class CostBasisDetail(BaseModel):
    model_config = {"populate_by_name": True}

    cost_basis: Optional[float] = Field(default=None, alias="costBasis")
    unadjusted_cost_basis: Optional[float] = Field(
        default=None, alias="unadjustedCostBasis"
    )
    disallowed_amount: Optional[float] = Field(default=None, alias="disallowedAmount")

    @field_validator("cost_basis", "unadjusted_cost_basis", "disallowed_amount", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class SecurityDetail(BaseModel):
    model_config = {"populate_by_name": True}

    asset_id: Optional[str] = Field(default=None, alias="assetId")
    security_short_description: Optional[str] = Field(
        default=None, alias="securityShortDescription"
    )


class ClosedPositionDetail(BaseModel):
    """Per-symbol closed position record within an account."""

    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    cusip: Optional[str] = None
    security_description: Optional[str] = Field(default=None, alias="securityDescription")
    security_type: Optional[str] = Field(default=None, alias="securityType")
    quantity: Optional[float] = None
    proceeds_amt: Optional[float] = Field(default=None, alias="proceedsAmt")
    is_all_basis_available: Optional[bool] = Field(
        default=None, alias="isAllBasisAvailable"
    )
    is_wash_sale_adjusted: Optional[bool] = Field(
        default=None, alias="isWashSaleAdjusted"
    )
    intraday_eligibility_code: Optional[str] = Field(
        default=None, alias="intradayEligibilityCode"
    )
    security_detail: Optional[SecurityDetail] = Field(
        default=None, alias="securityDetail"
    )
    cost_basis_detail: Optional[CostBasisDetail] = Field(
        default=None, alias="costBasisDetail"
    )
    long_term_gain_loss_detail: Optional[GainLossDetail] = Field(
        default=None, alias="longTermGainLossDetail"
    )
    total_gain_loss_detail: Optional[GainLossDetail] = Field(
        default=None, alias="totalGainLossDetail"
    )
    today_gain_loss_since_purchase: Optional[float] = Field(
        default=None, alias="todayGainLossSincePurchase"
    )
    today_gain_loss_since_prior_close: Optional[float] = Field(
        default=None, alias="todayGainLossSincePriorClose"
    )

    @field_validator(
        "quantity",
        "proceeds_amt",
        "today_gain_loss_since_purchase",
        "today_gain_loss_since_prior_close",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class AccountClosedPositionDetail(BaseModel):
    """Per-account summary with nested closed position records."""

    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    closed_position_count: Optional[int] = Field(
        default=None, alias="closedPositionCount"
    )
    proceeds_amt_total: Optional[float] = Field(
        default=None, alias="proceedsAmtTotal"
    )
    cost_basis_total: Optional[float] = Field(default=None, alias="costBasisTotal")
    long_term_gain_loss_detail: Optional[GainLossDetail] = Field(
        default=None, alias="longTermGainLossDetail"
    )
    total_gain_loss_detail: Optional[GainLossDetail] = Field(
        default=None, alias="totalGainLossDetail"
    )
    closed_positions: list[ClosedPositionDetail] = Field(default_factory=list)

    @field_validator("proceeds_amt_total", "cost_basis_total", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)

    @model_validator(mode="before")
    @classmethod
    def _extract_closed_positions(cls, data: Any) -> Any:
        """Flatten closedPositionDetails[] into closed_positions."""
        if not isinstance(data, dict):
            return data
        if "closed_positions" not in data:
            data = dict(data)
            data["closed_positions"] = data.get("closedPositionDetails") or []
        return data


class PortfolioGainLossDetail(BaseModel):
    model_config = {"populate_by_name": True}

    short_term_total_gain_loss: Optional[float] = Field(
        default=None, alias="shortTermTotalGainLoss"
    )
    long_term_total_gain_loss: Optional[float] = Field(
        default=None, alias="longTermTotalGainLoss"
    )
    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")

    @field_validator(
        "short_term_total_gain_loss",
        "long_term_total_gain_loss",
        "total_gain_loss",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class PortfolioDetail(BaseModel):
    model_config = {"populate_by_name": True}

    portfolio_gain_loss_detail: Optional[PortfolioGainLossDetail] = Field(
        default=None, alias="portfolioGainLossDetail"
    )
    proceeds_amt_total: Optional[float] = Field(
        default=None, alias="proceedsAmtTotal"
    )
    cost_basis_total: Optional[float] = Field(default=None, alias="costBasisTotal")

    @field_validator("proceeds_amt_total", "cost_basis_total", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------


class ClosedPositionsResponse(BaseModel):
    model_config = {"populate_by_name": True}

    portfolio_detail: Optional[PortfolioDetail] = None
    accounts: list[AccountClosedPositionDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "ClosedPositionsResponse":
        """Parse the full API JSON response into a ClosedPositionsResponse.

        Expected shape::

            {
                "closedPosition": {
                    "portfolioDetail": {...},
                    "acctDetails": {
                        "acctDetail": [...]
                    }
                }
            }
        """
        closed_position = data.get("closedPosition") or {}
        portfolio_detail_data = closed_position.get("portfolioDetail")
        acct_list = (
            (closed_position.get("acctDetails") or {}).get("acctDetail") or []
        )
        return cls(
            portfolio_detail=PortfolioDetail.model_validate(portfolio_detail_data)
            if portfolio_detail_data
            else None,
            accounts=[
                AccountClosedPositionDetail.model_validate(a) for a in acct_list
            ],
        )
