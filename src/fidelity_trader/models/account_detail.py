from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


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
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class PreferenceDetail(BaseModel):
    model_config = {"populate_by_name": True}

    name: Optional[str] = None
    is_hidden: Optional[bool] = Field(default=None, alias="isHidden")
    acct_group_id: Optional[str] = Field(default=None, alias="acctGroupId")
    is_default_acct: Optional[bool] = Field(default=None, alias="isDefaultAcct")


class TradeAttrDetail(BaseModel):
    model_config = {"populate_by_name": True}

    option_level: Optional[int] = Field(default=None, alias="optionLevel")
    mrgn_estb: Optional[bool] = Field(default=None, alias="mrgnEstb")
    option_estb: Optional[bool] = Field(default=None, alias="optionEstb")


class LegalAttrDetail(BaseModel):
    model_config = {"populate_by_name": True}

    legal_construct_code: Optional[str] = Field(default=None, alias="legalConstructCode")
    offering_code: Optional[str] = Field(default=None, alias="offeringCode")
    line_of_business_code: Optional[str] = Field(default=None, alias="lineOfBusinessCode")


class WorkplacePlanDetail(BaseModel):
    model_config = {"populate_by_name": True}

    market_value: Optional[float] = Field(default=None, alias="marketValue")
    plan_type_name: Optional[str] = Field(default=None, alias="planTypeName")
    plan_type: Optional[str] = Field(default=None, alias="planType")
    vested_acct_val_eod: Optional[float] = Field(default=None, alias="vestedAcctValEOD")
    client_id: Optional[str] = Field(default=None, alias="clientId")
    is_vested_100_pct: Optional[bool] = Field(default=None, alias="isVested100Pct")

    @field_validator("market_value", "vested_acct_val_eod", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


# ---------------------------------------------------------------------------
# Top-level account detail
# ---------------------------------------------------------------------------

class AccountDetail(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    acct_type: Optional[str] = Field(default=None, alias="acctType")
    acct_sub_type: Optional[str] = Field(default=None, alias="acctSubType")
    acct_sub_type_desc: Optional[str] = Field(default=None, alias="acctSubTypeDesc")
    preference_detail: Optional[PreferenceDetail] = Field(default=None, alias="preferenceDetail")
    acct_trade_attr_detail: Optional[TradeAttrDetail] = Field(default=None, alias="acctTradeAttrDetail")
    acct_legal_attr_detail: Optional[LegalAttrDetail] = Field(default=None, alias="acctLegalAttrDetail")
    workplace_plan_detail: Optional[WorkplacePlanDetail] = Field(default=None, alias="workplacePlanDetail")


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class AccountsResponse(BaseModel):
    model_config = {"populate_by_name": True}

    accounts: List[AccountDetail] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "AccountsResponse":
        """Parse the full API JSON response into an AccountsResponse.

        Expected shape::

            {
                "acctDetails": [
                    {
                        "acctNum": "...",
                        "acctType": "...",
                        ...
                    },
                    ...
                ]
            }
        """
        acct_list = data.get("acctDetails") or []
        return cls(
            accounts=[AccountDetail.model_validate(item) for item in acct_list]
        )
