from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from fidelity_trader.models.account import _parse_float


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class CollateralDetail(BaseModel):
    model_config = {"populate_by_name": True}

    cusip: Optional[str] = None
    cusip_desc: Optional[str] = Field(default=None, alias="cusipDesc")
    amount: Optional[float] = None

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class ContractDataDetail(BaseModel):
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None
    cusip: Optional[str] = None
    security_description: Optional[str] = Field(default=None, alias="securityDescription")
    rate: Optional[float] = None
    contract_val: Optional[float] = Field(default=None, alias="contractVal")
    contract_qty: Optional[float] = Field(default=None, alias="contractQty")
    prior_day_accrual: Optional[float] = Field(default=None, alias="priorDayAccrual")
    month_to_date_accrual: Optional[float] = Field(default=None, alias="monthToDateAccrual")

    @field_validator(
        "rate",
        "contract_val",
        "contract_qty",
        "prior_day_accrual",
        "month_to_date_accrual",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class AccountLoanedSecurities(BaseModel):
    model_config = {"populate_by_name": True}

    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    prior_day_accruals: Optional[float] = Field(default=None, alias="priorDayAccruals")
    month_to_date_accruals: Optional[float] = Field(default=None, alias="monthToDateAccruals")
    prior_month_accruals: Optional[float] = Field(default=None, alias="priorMonthAccruals")
    contract_data_details: list[ContractDataDetail] = Field(default_factory=list)
    collateral_details: list[CollateralDetail] = Field(default_factory=list)

    @field_validator(
        "prior_day_accruals",
        "month_to_date_accruals",
        "prior_month_accruals",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)

    @model_validator(mode="before")
    @classmethod
    def _extract_nested_lists(cls, data: Any) -> Any:
        """Flatten contractDataDetails.contractDataDetail[] and collateralDetails.collateralDetail[]."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if "contract_data_details" not in data:
            contract_data = data.get("contractDataDetails") or {}
            data["contract_data_details"] = contract_data.get("contractDataDetail") or []
        if "collateral_details" not in data:
            collateral_data = data.get("collateralDetails") or {}
            data["collateral_details"] = collateral_data.get("collateralDetail") or []
        return data


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------

class LoanedSecuritiesResponse(BaseModel):
    model_config = {"populate_by_name": True}

    accounts: list[AccountLoanedSecurities] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> "LoanedSecuritiesResponse":
        """Parse the full API JSON response into a LoanedSecuritiesResponse.

        Expected shape::

            {
                "loanedSecurities": {
                    "acctDetails": {
                        "acctDetail": [...]
                    }
                }
            }
        """
        loaned = data.get("loanedSecurities") or {}
        acct_list = (loaned.get("acctDetails") or {}).get("acctDetail") or []
        return cls(
            accounts=[AccountLoanedSecurities.model_validate(a) for a in acct_list],
        )
