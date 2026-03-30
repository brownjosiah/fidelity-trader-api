from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_float(v: Any) -> Optional[float]:
    """Convert a raw API value to float, handling None / sentinel strings."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s in ("", "--", "N/A"):
        return None
    # Remove thousands separators before converting
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(v: Any) -> Optional[int]:
    """Convert a raw API value to int, handling None / sentinel strings."""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    s = str(v).strip()
    if s in ("", "--", "N/A"):
        return None
    s = s.replace(",", "")
    try:
        return int(float(s))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Account(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    acct_type: Optional[str] = Field(default=None, alias="acctType")
    acct_sub_type: Optional[str] = None
    acct_sub_type_desc: Optional[str] = None
    nickname: Optional[str] = None
    option_level: Optional[int] = None
    is_margin: Optional[bool] = None
    is_options_enabled: Optional[bool] = None
    is_retirement: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def _extract_nested(cls, data: Any) -> Any:
        """Pull fields from preferenceDetail and acctTradeAttrDetail sub-dicts."""
        if not isinstance(data, dict):
            return data

        # Nickname from preferenceDetail.acctNickName
        pref = data.get("preferenceDetail") or {}
        if pref.get("acctNickName") and "nickname" not in data:
            data = dict(data)
            data["nickname"] = pref["acctNickName"]

        # Option level, margin, options enabled from acctTradeAttrDetail
        trade_attr = data.get("acctTradeAttrDetail") or {}
        if trade_attr:
            data = dict(data)
            if "option_level" not in data and "optionLevel" not in data:
                raw_level = trade_attr.get("optionLevel")
                if raw_level is not None:
                    data["option_level"] = _parse_int(raw_level)

            if "is_margin" not in data and "mrgnEstb" not in data:
                mrgn = trade_attr.get("mrgnEstb")
                if mrgn is not None:
                    data["is_margin"] = bool(mrgn) if isinstance(mrgn, bool) else str(mrgn).upper() in ("Y", "YES", "TRUE", "1")

            if "is_options_enabled" not in data and "optionEstb" not in data:
                opt_estb = trade_attr.get("optionEstb")
                if opt_estb is not None:
                    data["is_options_enabled"] = bool(opt_estb) if isinstance(opt_estb, bool) else str(opt_estb).upper() in ("Y", "YES", "TRUE", "1")

        return data


class Balance(BaseModel):
    model_config = {"populate_by_name": True}

    total_account_value: Optional[float] = Field(default=None, alias="totalAcctVal")
    cash_available: Optional[float] = Field(default=None, alias="cashAvailForTrade")
    intraday_buying_power: Optional[float] = Field(default=None, alias="intraDayBP")
    margin_buying_power: Optional[float] = Field(default=None, alias="mrgnBP")
    non_margin_buying_power: Optional[float] = Field(default=None, alias="nonMrgnBP")
    is_margin_account: Optional[bool] = Field(default=None, alias="isMrgnAcct")

    @field_validator(
        "total_account_value",
        "cash_available",
        "intraday_buying_power",
        "margin_buying_power",
        "non_margin_buying_power",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class Position(BaseModel):
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    security_type: Optional[str] = Field(default=None, alias="securityType")
    quantity: Optional[float] = None
    last_price: Optional[float] = Field(default=None, alias="lastPrice")
    market_value: Optional[float] = Field(default=None, alias="marketValue")
    cost_basis: Optional[float] = Field(default=None, alias="costBasis")
    gain_loss: Optional[float] = Field(default=None, alias="gainLoss")
    gain_loss_pct: Optional[float] = Field(default=None, alias="gainLossPct")

    @field_validator(
        "quantity",
        "last_price",
        "market_value",
        "cost_basis",
        "gain_loss",
        "gain_loss_pct",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)
