from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from fidelity_trader.models.account import _parse_float


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class GainLossDetail(BaseModel):
    model_config = {"populate_by_name": True}

    total_cost_basis: Optional[float] = Field(default=None, alias="totalCostBasis")
    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")
    total_market_value: Optional[float] = Field(default=None, alias="totalMarketValue")
    total_gain_loss_pct: Optional[float] = Field(default=None, alias="totalGainLossPct")

    @field_validator(
        "total_cost_basis",
        "total_gain_loss",
        "total_market_value",
        "total_gain_loss_pct",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class LegPriceDetail(BaseModel):
    model_config = {"populate_by_name": True}

    leg_option_price: Optional[float] = Field(default=None, alias="legOptionPrice")
    leg_option_last_price: Optional[float] = Field(default=None, alias="legOptionLastPrice")
    leg_option_price_chg: Optional[float] = Field(default=None, alias="legOptionPriceChg")
    leg_expiration_date: Optional[str] = Field(default=None, alias="legExpirationDate")
    leg_expiration_days: Optional[int] = Field(default=None, alias="legExpirationDays")
    leg_option_strike_price: Optional[float] = Field(default=None, alias="legOptionStrikePrice")

    @field_validator(
        "leg_option_price",
        "leg_option_last_price",
        "leg_option_price_chg",
        "leg_option_strike_price",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class LegSecurityDetails(BaseModel):
    model_config = {"populate_by_name": True}

    leg_symbol: Optional[str] = Field(default=None, alias="legSymbol")
    leg_security_description: Optional[str] = Field(default=None, alias="legSecurityDescription")
    leg_symbol_expiry_date: Optional[str] = Field(default=None, alias="legSymbolExpiryDate")
    leg_symbol_pc_index: Optional[str] = Field(default=None, alias="legSymbolPCIndex")
    leg_symbol_strike: Optional[float] = Field(default=None, alias="legSymbolStrike")
    del_shares: Optional[int] = Field(default=None, alias="delShares")

    @field_validator("leg_symbol_strike", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class LegMarketValDetail(BaseModel):
    model_config = {"populate_by_name": True}

    market_val: Optional[float] = Field(default=None, alias="marketVal")
    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")
    total_gain_loss_pct: Optional[float] = Field(default=None, alias="totalGainLossPct")

    @field_validator("market_val", "total_gain_loss", "total_gain_loss_pct", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class LegDetail(BaseModel):
    model_config = {"populate_by_name": True}

    leg_buy_sell_ind: Optional[str] = Field(default=None, alias="legBuySellInd")
    leg_shares: Optional[float] = Field(default=None, alias="legShares")
    leg_in_the_money_index: Optional[str] = Field(default=None, alias="legInTheMoneyIndex")
    leg_option_security_type_code: Optional[str] = Field(default=None, alias="legOptionSecurityTypeCode")
    market_val_detail: Optional[LegMarketValDetail] = Field(default=None, alias="marketValDetail")
    leg_security_details: Optional[LegSecurityDetails] = Field(default=None, alias="legSecurityDetails")
    leg_price_detail: Optional[LegPriceDetail] = Field(default=None, alias="legPriceDetail")

    @field_validator("leg_shares", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class PairingSecurityDetails(BaseModel):
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    security_description: Optional[str] = Field(default=None, alias="securityDescription")
    ul_price: Optional[float] = Field(default=None, alias="ulPrice")
    last_price: Optional[float] = Field(default=None, alias="lastPrice")
    last_price_chg: Optional[float] = Field(default=None, alias="lastPriceChg")
    last_price_chg_pct: Optional[float] = Field(default=None, alias="lastPriceChgPct")

    @field_validator("ul_price", "last_price", "last_price_chg", "last_price_chg_pct", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)

    @model_validator(mode="before")
    @classmethod
    def _flatten_price_detail(cls, data: Any) -> Any:
        """Hoist priceDetail fields up to the top level."""
        if not isinstance(data, dict):
            return data
        price_detail = data.get("priceDetail")
        if not price_detail:
            return data
        data = dict(data)
        for key in ("ulPrice", "lastPrice", "lastPriceChg", "lastPriceChgPct"):
            if key not in data and key in price_detail:
                data[key] = price_detail[key]
        return data


class PairingDetail(BaseModel):
    model_config = {"populate_by_name": True}

    pairing_security_details: Optional[PairingSecurityDetails] = Field(
        default=None, alias="pairingSecurityDetails"
    )
    option_pair_match_code: Optional[str] = Field(default=None, alias="optionPairMatchCode")
    option_pair_match_code_description: Optional[str] = Field(
        default=None, alias="optionPairMatchCodeDescription"
    )
    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")
    total_market_value: Optional[float] = Field(default=None, alias="totalMarketValue")
    total_cost_basis: Optional[float] = Field(default=None, alias="totalCostBasis")
    leg_count: Optional[int] = Field(default=None, alias="legCount")
    legs: List[LegDetail] = Field(default_factory=list)

    @field_validator("total_gain_loss", "total_market_value", "total_cost_basis", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)

    @model_validator(mode="before")
    @classmethod
    def _extract_legs(cls, data: Any) -> Any:
        """Flatten legDetails.legDetail[] into legs."""
        if not isinstance(data, dict):
            return data
        if "legs" not in data:
            leg_details = data.get("legDetails") or {}
            leg_list = leg_details.get("legDetail") or []
            data = dict(data)
            data["legs"] = leg_list
        return data


class UnderlyingDetail(BaseModel):
    model_config = {"populate_by_name": True}

    leg_expiration_date: Optional[str] = Field(default=None, alias="legExpirationDate")
    leg_expiration_days: Optional[int] = Field(default=None, alias="legExpirationDays")
    pairing_count: Optional[int] = Field(default=None, alias="pairingCount")
    total_gain_loss: Optional[float] = Field(default=None, alias="totalGainLoss")
    total_gain_loss_pct: Optional[float] = Field(default=None, alias="totalGainLossPct")
    total_market_value: Optional[float] = Field(default=None, alias="totalMarketValue")
    total_cost_basis: Optional[float] = Field(default=None, alias="totalCostBasis")
    pairings: List[PairingDetail] = Field(default_factory=list)

    @field_validator(
        "total_gain_loss",
        "total_gain_loss_pct",
        "total_market_value",
        "total_cost_basis",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)

    @model_validator(mode="before")
    @classmethod
    def _extract_pairings(cls, data: Any) -> Any:
        """Flatten pairingDetails.pairingDetail[] into pairings."""
        if not isinstance(data, dict):
            return data
        if "pairings" not in data:
            pairing_details = data.get("pairingDetails") or {}
            pairing_list = pairing_details.get("pairingDetail") or []
            data = dict(data)
            data["pairings"] = pairing_list
        return data


class OptionAccountDetail(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: str = Field(alias="acctNum")
    cycle_date: Optional[str] = Field(default=None, alias="cycleDate")
    cycle_time: Optional[str] = Field(default=None, alias="cycleTime")
    underlying_count: Optional[int] = Field(default=None, alias="underlyingCount")
    count: Optional[int] = None
    account_gain_loss_detail: Optional[GainLossDetail] = Field(
        default=None, alias="accountGainLossDetail"
    )
    option_gain_loss_detail: Optional[GainLossDetail] = Field(
        default=None, alias="optionGainLossDetail"
    )
    underlying_details: List[UnderlyingDetail] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _extract_underlying_details(cls, data: Any) -> Any:
        """Flatten underlyingDetails.underlyingDetail[] into underlying_details."""
        if not isinstance(data, dict):
            return data
        if "underlying_details" not in data:
            ud_wrapper = data.get("underlyingDetails") or {}
            ud_list = ud_wrapper.get("underlyingDetail") or []
            data = dict(data)
            data["underlying_details"] = ud_list
        return data


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class OptionSummaryResponse(BaseModel):
    model_config = {"populate_by_name": True}

    accounts: List[OptionAccountDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "OptionSummaryResponse":
        """Parse the full API JSON response into an OptionSummaryResponse.

        Expected shape::

            {
                "optionPairing": {
                    "acctDetails": [
                        {
                            "acctDetail": { ... }
                        },
                        ...
                    ]
                }
            }
        """
        option_pairing = data.get("optionPairing") or {}
        acct_details_list = option_pairing.get("acctDetails") or []
        accounts = []
        for item in acct_details_list:
            acct_detail = item.get("acctDetail") if isinstance(item, dict) else None
            if acct_detail:
                accounts.append(OptionAccountDetail.model_validate(acct_detail))
        return cls(accounts=accounts)
