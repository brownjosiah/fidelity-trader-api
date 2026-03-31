from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from fidelity_trader.models.account import _parse_float


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class SecurityDetail(BaseModel):
    model_config = {"populate_by_name": True}

    symbol: Optional[str] = None


class TaxLotSummary(BaseModel):
    model_config = {"populate_by_name": True}

    num_of_lots_total: Optional[int] = Field(default=None, alias="numOfLotsTotal")
    num_of_lots: Optional[int] = Field(default=None, alias="numOfLots")


class TaxLotAccountingDetail(BaseModel):
    model_config = {"populate_by_name": True}

    qty: Optional[float] = None
    term: Optional[str] = None
    acquisition_price: Optional[float] = Field(default=None, alias="acquisitionPrice")
    cost_basis: Optional[float] = Field(default=None, alias="costBasis")
    unrealized_gain_loss: Optional[float] = Field(default=None, alias="unrealizedGainLoss")
    source: Optional[str] = None
    wash_sale_ind: Optional[bool] = Field(default=None, alias="washSaleInd")
    disqualified_display_type_code: Optional[str] = Field(
        default=None, alias="disqualifiedDisplayTypeCode"
    )
    event_id_orig: Optional[str] = Field(default=None, alias="eventIdOrig")
    local_tla_basis_per_share: Optional[str] = Field(
        default=None, alias="localTLABasisPerShare"
    )
    local_tla_total_basis: Optional[str] = Field(default=None, alias="localTLATotalBasis")
    local_unrealized_gain_loss: Optional[str] = Field(
        default=None, alias="localUnrealizedGainLoss"
    )
    event_id: Optional[str] = Field(default=None, alias="eventId")
    acquisition_date: Optional[int] = Field(default=None, alias="acquisitionDate")
    avg_cost_per_share: Optional[float] = Field(default=None, alias="avgCostPerShare")

    @field_validator(
        "qty",
        "acquisition_price",
        "cost_basis",
        "unrealized_gain_loss",
        "avg_cost_per_share",
        mode="before",
    )
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class TaxLotDetail(BaseModel):
    model_config = {"populate_by_name": True}

    lot_seq: Optional[int] = Field(default=None, alias="lotSeq")
    lot_qty: Optional[float] = Field(default=None, alias="lotQty")
    specific_shr_tax_lot_accounting_detail: Optional[TaxLotAccountingDetail] = Field(
        default=None, alias="specificShrTaxLotAccountingDetail"
    )

    @field_validator("lot_qty", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)


class SpecificShrTaxLotDetail(BaseModel):
    model_config = {"populate_by_name": True}

    specific_shr_tax_lot_details: list[TaxLotDetail] = Field(
        default_factory=list, alias="specificShrTaxLotDetails"
    )
    num_of_lots: Optional[int] = Field(default=None, alias="numOfLots")
    summary: Optional[TaxLotSummary] = None


# ---------------------------------------------------------------------------
# Top-level response
# ---------------------------------------------------------------------------


class TaxLotResponse(BaseModel):
    model_config = {"populate_by_name": True}

    security_detail: Optional[SecurityDetail] = Field(
        default=None, alias="securityDetail"
    )
    exec_qty: Optional[float] = Field(default=None, alias="execQty")
    specific_shr_tax_lot_detail: Optional[SpecificShrTaxLotDetail] = Field(
        default=None, alias="specificShrTaxLotDetail"
    )
    acct_num: Optional[str] = Field(default=None, alias="acctNum")
    acct_type_code: Optional[int] = Field(default=None, alias="acctTypeCode")
    lot_curr_ind: Optional[str] = Field(default=None, alias="lotCurrInd")

    @field_validator("exec_qty", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        return _parse_float(v)

    @classmethod
    def from_api_response(cls, data: dict) -> "TaxLotResponse":
        """Parse the full API JSON response into a TaxLotResponse.

        Expected shape (the API returns the response body directly)::

            {
                "securityDetail": {"symbol": "LGVN"},
                "execQty": 0.0,
                "specificShrTaxLotDetail": {
                    "specificShrTaxLotDetails": [...],
                    "numOfLots": 0,
                    "summary": {...}
                },
                "acctNum": "Z25485019",
                "acctTypeCode": 1,
                "lotCurrInd": "false"
            }
        """
        return cls.model_validate(data)
